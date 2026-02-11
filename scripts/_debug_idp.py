"""Debug: list identity providers and system auth sources from the Endor Labs API."""

from endorlabs.api_client import APIClient


def main() -> None:
    c = APIClient(auth_method="api-key")

    # Check system-level identity providers
    for ns in ["endor-solutions-tgowan", "system"]:
        resp = c.get(f"v1/namespaces/{ns}/identity-providers")
        print(f"[{ns}] identity-providers: {resp.status_code}")
        if resp.status_code == 200:
            import json

            data = resp.json()
            objs = data.get("list", {}).get("objects", [])
            print(f"  Found {len(objs)} identity providers")
            for p in objs:
                print(f"  - {p.get('meta', {}).get('name', '?')} (uuid={p.get('uuid', '?')})")
        print()

    # Try to get the existing OIDC policy and inspect its full API response
    resp = c.get(
        "v1/namespaces/endor-solutions-tgowan/authorization-policies",
        params={
            "list_parameters.filter": 'meta.name=="GitHub Actions OIDC - Endor-Solutions-Architecture"',
        },
    )
    print(f"OIDC policy search: {resp.status_code}")
    if resp.status_code == 200:
        import json

        data = resp.json()
        objs = data.get("list", {}).get("objects", [])
        if objs:
            print(json.dumps(objs[0].get("spec", {}), indent=2))

    c.close()


if __name__ == "__main__":
    main()
