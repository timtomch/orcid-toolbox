"""Utilities for fetching ORCID publication data.

Provides `fetch_orcid_publications(orcid, timeout=10)` which returns a
dictionary containing a list of publications for the given ORCID iD using
the public ORCID API (v3.0).

The function is intentionally lightweight and depends only on `requests`.
"""
from typing import Any, Dict, List, Optional
import re

import requests


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


def fetch_orcid_data(orcid: str, timeout: int = 10) -> Dict[str, Any]:
	"""Fetch publications for an ORCID iD from the public ORCID API.

	Args:
	  orcid: ORCID iD in dashed 16-digit form.
	  timeout: Request timeout in seconds.

	Returns:
	  A dict with keys: `orcid`, `count`, `publications` (list), and `raw`
	  (the raw JSON returned by ORCID).

	Raises:
	  ValueError: if ORCID format is invalid.
	  requests.HTTPError: if the HTTP request fails with non-200 status.
	  requests.RequestException: for other network-related errors.
	"""
	url = f"https://pub.orcid.org/v3.0/{orcid}/record"
	headers = {"Accept": "application/json"}

	resp = requests.get(url, headers=headers, timeout=timeout)
	if resp.status_code == 404:
		# No record found for ORCID -> return empty result
		return {"orcid": orcid, "name": "", "count": 0, "publications": [], "raw": None}
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
		# Each group may contain multiple "work-summary" entries; pick the
		# first summary as the representative.
		summaries = group.get("work-summary") or []
		if not summaries:
			continue
		summary = summaries[0]

		external_ids = _extract_external_ids(summary)
		dois = [e["doi"] for e in external_ids if e.get("doi")]

		pub: Dict[str, Any] = {
			"put-code": summary.get("put-code"),
			"title": _safe_get_title(summary),
			"type": summary.get("type"),
			"journal-title": summary.get("journal-title"),
			"publication-date": summary.get("publication-date"),
			"external-ids": _extract_external_ids(summary),
			"visibility": summary.get("visibility"),
			"url": summary.get("url", {}).get("value") if summary.get("url") else None,
			"doi": dois[0] if dois else None,
		}
		publications.append(pub)

	return {"orcid": orcid, "name": researcher_name, "count": len(publications), "publications": publications, "raw": data}