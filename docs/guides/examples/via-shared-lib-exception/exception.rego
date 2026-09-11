# Exception: vulnerability leaf sits under a direct shared library.
#
# Model: shared lib is a DIRECT dependency of the consumer PackageVersion,
# the finding DependencyMetadata sits in that library subtree
# (parent_version_name walk), and the analyzed PackageVersion is not the
# shared library itself.
#
# Create as POLICY_TYPE_EXCEPTION:
#   Query statement: via_shared_lib_exception.match_finding
#   Resource kinds: Finding, DependencyMetadata, PackageVersion
#   Scope: consumer projects only (exclude the shared-lib producer project)
#   Start with disable=true until a live dry-run or rescan looks right.
#
# Platform rejects Rego recursion; parent walk is unrolled to depth 0..6.
# Use distinct rule names for depth helpers vs the 2-arg OR wrapper
# (same name at two arities is a type conflict).
#
# Do not use SCA template Dependency Name = the shared lib (that matches
# findings on the shared lib leaf, not vulns via its subtree).
# FINDING_TAGS_PATH_EXTERNAL can work for polyrepo-only topologies; it does
# not fire in monorepos. PolicyValidation compile-check is fine; match proof
# needs a live DependencyMetadata parent walk or enable+rescan.
#
# Important: do not put a "data.<package>" path in comments — PolicyValidation
# may treat that text as a data reference and fail compile-check.

package via_shared_lib_exception

# --- knob (coordinate substring of the shared library PackageVersion / DM name) ---
shared_lib_substr := "com.example.shared:common-lib"

# --- helpers ---

contains_ci(s, sub) {
	contains(lower(s), lower(sub))
}

# Resolve parent_name -> DM under the same importer PackageVersion.
dm_named(importer_uuid, name) = dm {
	some i
	dm := data.resources.DependencyMetadata[i]
	dm.meta.parent_uuid == importer_uuid
	dm.meta.name == name
}

# True when shared lib is a DIRECT dependency of this importer PV.
shared_lib_is_direct(importer_uuid) {
	some i
	dm := data.resources.DependencyMetadata[i]
	dm.meta.parent_uuid == importer_uuid
	contains_ci(dm.meta.name, shared_lib_substr)
	dm.spec.dependency_data.direct == true
}

# Depth 0: immediate parent_version_name is the shared lib.
via_at_depth(importer_uuid, parent_name, 0) {
	parent_name != ""
	contains_ci(parent_name, shared_lib_substr)
}

# Depth 1..6: walk one hop per rule (unrolled recursion).
via_at_depth(importer_uuid, parent_name, 1) {
	parent_name != ""
	dm := dm_named(importer_uuid, parent_name)
	contains_ci(dm.spec.dependency_data.parent_version_name, shared_lib_substr)
}

via_at_depth(importer_uuid, parent_name, 2) {
	parent_name != ""
	d1 := dm_named(importer_uuid, parent_name)
	d2 := dm_named(importer_uuid, d1.spec.dependency_data.parent_version_name)
	contains_ci(d2.spec.dependency_data.parent_version_name, shared_lib_substr)
}

via_at_depth(importer_uuid, parent_name, 3) {
	parent_name != ""
	d1 := dm_named(importer_uuid, parent_name)
	d2 := dm_named(importer_uuid, d1.spec.dependency_data.parent_version_name)
	d3 := dm_named(importer_uuid, d2.spec.dependency_data.parent_version_name)
	contains_ci(d3.spec.dependency_data.parent_version_name, shared_lib_substr)
}

via_at_depth(importer_uuid, parent_name, 4) {
	parent_name != ""
	d1 := dm_named(importer_uuid, parent_name)
	d2 := dm_named(importer_uuid, d1.spec.dependency_data.parent_version_name)
	d3 := dm_named(importer_uuid, d2.spec.dependency_data.parent_version_name)
	d4 := dm_named(importer_uuid, d3.spec.dependency_data.parent_version_name)
	contains_ci(d4.spec.dependency_data.parent_version_name, shared_lib_substr)
}

via_at_depth(importer_uuid, parent_name, 5) {
	parent_name != ""
	d1 := dm_named(importer_uuid, parent_name)
	d2 := dm_named(importer_uuid, d1.spec.dependency_data.parent_version_name)
	d3 := dm_named(importer_uuid, d2.spec.dependency_data.parent_version_name)
	d4 := dm_named(importer_uuid, d3.spec.dependency_data.parent_version_name)
	d5 := dm_named(importer_uuid, d4.spec.dependency_data.parent_version_name)
	contains_ci(d5.spec.dependency_data.parent_version_name, shared_lib_substr)
}

via_at_depth(importer_uuid, parent_name, 6) {
	parent_name != ""
	d1 := dm_named(importer_uuid, parent_name)
	d2 := dm_named(importer_uuid, d1.spec.dependency_data.parent_version_name)
	d3 := dm_named(importer_uuid, d2.spec.dependency_data.parent_version_name)
	d4 := dm_named(importer_uuid, d3.spec.dependency_data.parent_version_name)
	d5 := dm_named(importer_uuid, d4.spec.dependency_data.parent_version_name)
	d6 := dm_named(importer_uuid, d5.spec.dependency_data.parent_version_name)
	contains_ci(d6.spec.dependency_data.parent_version_name, shared_lib_substr)
}

via_shared_lib(importer_uuid, parent_name) {
	via_at_depth(importer_uuid, parent_name, 0)
}

via_shared_lib(importer_uuid, parent_name) {
	via_at_depth(importer_uuid, parent_name, 1)
}

via_shared_lib(importer_uuid, parent_name) {
	via_at_depth(importer_uuid, parent_name, 2)
}

via_shared_lib(importer_uuid, parent_name) {
	via_at_depth(importer_uuid, parent_name, 3)
}

via_shared_lib(importer_uuid, parent_name) {
	via_at_depth(importer_uuid, parent_name, 4)
}

via_shared_lib(importer_uuid, parent_name) {
	via_at_depth(importer_uuid, parent_name, 5)
}

via_shared_lib(importer_uuid, parent_name) {
	via_at_depth(importer_uuid, parent_name, 6)
}

# --- main match ---

match_finding[result] {
	some i, j, k
	finding := data.resources.Finding[i]
	not finding.spec.dismiss

	# Consumers see leaf vulns as TRANSITIVE through the shared lib.
	finding.spec.finding_tags[_] == "FINDING_TAGS_TRANSITIVE"

	# Do not except findings whose importer PackageVersion is the shared lib
	# (monorepo: shared-lib module still has transitive children).
	importer := data.resources.PackageVersion[k]
	importer.uuid == finding.meta.parent_uuid
	not contains_ci(importer.meta.name, shared_lib_substr)

	dm := data.resources.DependencyMetadata[j]
	dm.uuid == finding.spec.target_uuid

	importer_uuid := dm.meta.parent_uuid
	shared_lib_is_direct(importer_uuid)
	via_shared_lib(importer_uuid, dm.spec.dependency_data.parent_version_name)

	result = {
		"Endor": {
			"Finding": finding.uuid,
		},
		"Target": finding.spec.target_dependency_package_name,
		"Via": shared_lib_substr,
	}
}
