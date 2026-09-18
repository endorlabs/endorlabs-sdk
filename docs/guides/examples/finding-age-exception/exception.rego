# Exception: vulnerability findings older than a threshold
#
# Age is Endor discovery age from Finding.meta.create_time
# (time since the finding was created in the tenant), NOT CVE
# first_published / advisory publish date.
#
# Create as POLICY_TYPE_EXCEPTION:
#   Query statement: finding_age_exception.match_finding
#   Resource kinds: Finding
#   Start with disable=true until a live dry-run looks right.
#
# Important: do not put a "data.<package>" path in comments —
# PolicyValidation may treat that text as a data reference and fail
# compile-check.

package finding_age_exception

# --- knob ---
min_age_days := 90

# --- helpers ---

age_days(finding) = days {
	create_ns := time.parse_rfc3339_ns(finding.meta.create_time)
	age_ns := time.now_ns() - create_ns
	days := age_ns / (24 * 60 * 60 * 1000000000)
}

# --- match ---

match_finding[result] {
	some i
	finding := data.resources.Finding[i]
	not finding.spec.dismiss
	finding.spec.finding_categories[_] == "FINDING_CATEGORY_VULNERABILITY"
	age_days(finding) >= min_age_days

	result = {
		"Endor": {
			"Finding": finding.uuid,
		},
		"AgeDays": age_days(finding),
		"MinAgeDays": min_age_days,
	}
}
