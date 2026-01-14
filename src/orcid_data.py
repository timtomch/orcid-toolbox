# Helper functions for ORCID data fetching and processing.
# Queries the public ORCID API (v3), no key necessary.
#
# Provided functions:
# - fetch_orcid_data(orcid, timeout=10): Fetches publication data for a given ORCID iD.
# - format_timestamp(timestamp, freshness=False): Formats a timestamp to human readable string.

from typing import Any, Dict, List, Optional
from datetime import datetime
import re
import requests
import pandas as pd

# Format a timestamp (in milliseconds since epoch) to a human-readable date string.
# If freshness is True, append a colored dot indicating how recent the date is.
# If return_status is True, returns a tuple (formatted_string, status) where status is "Fresh", "Aging", "Stale", or None.
# Otherwise, returns just the formatted string for backward compatibility.
def format_timestamp(timestamp: str, freshness: bool = False, return_status: bool = False) -> str | tuple[str, Optional[str]]:
	output_string= datetime.fromtimestamp(float(timestamp)/1000).strftime('%Y-%m-%d')
	output_freshness: Optional[str] = None
	if freshness:
		delta = datetime.now() - datetime.fromtimestamp(float(timestamp)/1000)
		days = delta.days
		if days > 365 * 2:
			output_string += " 🔴"
			output_freshness = "stale"
		elif days > 365:
			output_string += " 🟡"
			output_freshness = "aging"
		else:
			output_string += " 🟢"
			output_freshness = "fresh"
	
	if return_status:
		return (output_string, output_freshness)
	return output_string

_DOI_RE = re.compile(r"(10\.\d{4,9}/\S+)", re.IGNORECASE)

def _safe_get_title(summary: Dict[str, Any]) -> Optional[str]:
	# ORCID v3 JSON: title -> title -> value
	title = summary.get("title") or {}
	inner = title.get("title") if isinstance(title, dict) else None
	if isinstance(inner, dict):
		return inner.get("value")
	return None


def _extract_doi_from_external_id(item: Dict[str, Any]) -> Optional[str]:
	if not isinstance(item, dict):
		return None

	type_ = item.get("external-id-type") or ""
	if type_.lower() == "doi":	
		norm = item.get("external-id-normalized") or {}
		if isinstance(norm, dict):
			val = norm.get("value")
			if val:
				return val

	value = item.get("external-id-value") or ""
	if not isinstance(value, str):
		return None

	# common DOI url form
	m = re.search(r"doi\.org/(10\.\d{4,9}/\S+)", value, flags=re.IGNORECASE)
	if m:
		return m.group(1)

	# raw DOI anywhere in the string
	m2 = _DOI_RE.search(value)
	if m2:
		return m2.group(1)

	return None

# Processes external IDs from a work summary and extracts DOIs where available.
def _extract_external_ids(summary: Dict[str, Any]) -> List[Dict[str, str]]:
	out: List[Dict[str, str]] = []
	ext = summary.get("external-ids") or {}
	for item in ext.get("external-id", []) if isinstance(ext, dict) else []:
		doi = _extract_doi_from_external_id(item)
		out.append({
			"type": item.get("external-id-type"),
			"value": item.get("external-id-value"),
			"url": item.get("external-id-url", {}).get("value")
			if item.get("external-id-url")
			else None,
			"doi": doi,
		})
	return out

# Fetches ORCID data including publications for a given ORCID iD.
# Args:
#   orcid: ORCID iD in dashed 16-digit form.
#   timeout: Request timeout in seconds.
# Returns:
#   A tuple of (DataFrame, raw_json) where:
#   - DataFrame contains publication data
#   - raw_json is the full API response JSON object (or None if error)
def fetch_orcid_data(orcid: str, timeout: int = 10) -> tuple[pd.DataFrame, Optional[Dict[str, Any]], Optional[str], Optional[str]]:
	url = f"https://pub.orcid.org/v3.0/{orcid}/record"
	headers = {"Accept": "application/json"}

	resp = requests.get(url, headers=headers, timeout=timeout)
	if resp.status_code == 404:
		# No record found for ORCID -> return empty result
		empty_df = pd.DataFrame(
			columns=[
				"put-code",
				"modified-date",
				"modified-by",
				"title",
				"type",
				"journal-title",
				"publication-date",
				"external-ids",
				"visibility",
				"url",
				"doi"
			]
		)
		return (empty_df, None)
	try:
		resp.raise_for_status()
	except requests.HTTPError:
		# Attach response text for easier debugging
		raise requests.HTTPError(f"ORCID API error {resp.status_code}: {resp.text}")

	data = resp.json()

	researcher_givenname = data.get("person", {}).get("name", {}).get("given-names", {}).get("value", "")
	researcher_familyname = data.get("person", {}).get("name", {}).get("family-name", {}).get("value", "")
	researcher_name = f"{researcher_givenname} {researcher_familyname}".strip()

	groups = data.get("activities-summary", {}).get("works", {}).get("group", {}) if isinstance(data, dict) else []
	publications: List[Dict[str, Any]] = []

	for group in groups or []:
		# Each group contains grouped work objects. The first one is the one picked by the user.
		summaries = group.get("work-summary") or []
		if not summaries:
			continue
		summary = summaries[0]

		external_ids = _extract_external_ids(summary)
		dois = [e["doi"] for e in external_ids if e.get("doi")]

		pub: Dict[str, Any] = {
			"put-code": summary.get("put-code"),
			"modified-date": format_timestamp(summary.get("last-modified-date", {}).get("value")) if summary.get("last-modified-date") else None,
			"modified-by": summary.get("source", {}).get("source-name", {}).get("value"),
			"title": _safe_get_title(summary),
			"type": summary.get("type"),
			"journal-title": summary.get("journal-title", {}).get("value") if summary.get("journal-title") else None,
			"publication-year": summary.get("publication-date", {}).get("year", {}).get("value") if summary.get("publication-date") else None,
			"external-ids": _extract_external_ids(summary),
			"visibility": summary.get("visibility"),
			"url": summary.get("url", {}).get("value") if summary.get("url") else None,
			"doi": dois[0] if dois else None,
		}
		publications.append(pub)

	# Build a DataFrame from the extracted publications
	df = pd.DataFrame(publications)

	if df.empty:
		# Ensure an empty DataFrame has the expected columns
		df = pd.DataFrame(
			columns=[
				"put-code",
				"modified-date",
				"modified-by",
				"title",
				"type",
				"journal-title",
				"publication-year",
				"external-ids",
				"visibility",
				"url",
				"doi"
			]
		)
	return (df, data, orcid, researcher_name)