# Exception: finding leaf is reachable under a shared library in the BOM graph.
#
# Model: the importer PackageVersion dependency_graph has a path
#   parent -> ... -> shared lib -> ... -> finding target
# so the shared library sits on the path from the analyzed package to the leaf.
#
# Create as POLICY_TYPE_EXCEPTION:
#   Query statement: via_shared_lib_exception.match_finding
#   Resource kinds: Finding, PackageVersion
#   Scope: consumer projects only (exclude the shared-lib producer project)
#   Start with disable=true until validate + rescan look right.
#
# Uses OPA graph.reachable (builtin). Prefer this over:
#   - iterating dependency_graph keys for "shared lib present" (BOM-presence;
#     over-matches every transitive finding on that importer)
#   - Rego recursion / unrolled hop rules (recursion is rejected; hops are fragile)
#
# Do not use SCA template Dependency Name = the shared lib (that matches the
# leaf name, not an intermediate on the path).
#
# Avoid embedding a data-dot-package path in comments; PolicyValidation may
# treat that text as a data reference.

package via_shared_lib_exception

# Coordinate substring that must sit on the path to the finding.
# Example: "com.example.shared:common-lib" matches
# mvn://com.example.shared:common-lib@1.2.3
input_package := "com.example.shared:common-lib"

# Parent PackageVersions that have findings. Avoid walking unused graphs.
needed_pkg[uuid] {
	uuid := data.resources.Finding[_].meta.parent_uuid
}

# dependency_graph as node -> set of children, for graph.reachable.
adjacency[uuid] := adj {
	needed_pkg[uuid]
	some i
	pkg := data.resources.PackageVersion[i]
	pkg.uuid == uuid
	dep_graph := pkg.spec.resolved_dependencies.dependency_graph
	adj := {parent: children |
		some parent
		dep_graph[parent]
		children := {child | child := dep_graph[parent][_]}
	}
}

# Every node reachable from the parent package, including the parent.
from_root[uuid] := graph.reachable(adjacency[uuid], {name}) {
	some i
	pkg := data.resources.PackageVersion[i]
	pkg.uuid == uuid
	name := pkg.meta.name
}

# Every node reachable from input_package after it is reached from the parent.
# A finding target in this set has input_package on a path from the parent.
in_path[uuid] := graph.reachable(adjacency[uuid], starts) {
	some uuid
	from_root[uuid]
	starts := {mid |
		from_root[uuid][mid]
		contains(mid, input_package)
	}
}

# Match findings whose target dependency is downstream of input_package.
match_finding[result] {
	some i, k
	f := data.resources.Finding[i]
	pkg := data.resources.PackageVersion[k]
	pkg.uuid == f.meta.parent_uuid

	# Do not except findings owned by the shared-lib PackageVersion itself.
	not contains(pkg.meta.name, input_package)

	# Do not except when the leaf *is* the shared library.
	not contains(f.spec.target_dependency_package_name, input_package)

	in_path[f.meta.parent_uuid][f.spec.target_dependency_package_name]

	result = {
		"Endor": {
			"Finding": f.uuid,
		},
	}
}
