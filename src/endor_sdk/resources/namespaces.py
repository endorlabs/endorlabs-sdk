from ..api_client import APIClient
import json
from pydantic import BaseModel
from typing import List

# Pydantic Models for Namespace data
class NamespaceMeta(BaseModel):
    name: str
    description: str

class Namespace(BaseModel):
    uuid: str
    meta: NamespaceMeta

class CreateNamespacePayload(BaseModel):
    meta: NamespaceMeta


def list_namespaces(client: APIClient, tenant_namespace: str) -> List[Namespace]:
    try:
        headers = client.default_headers
        res = client.get(f'v1/namespaces/{tenant_namespace}/namespaces', headers=client.default_headers)
        data = res.json().get('list', {}).get("objects", [])
        return [Namespace(**item) for item in data]
    except Exception as e:
        print(f"Error listing namespaces: {e}")
        return []

def create_namespace(client: APIClient, parent_namespace: str, payload: CreateNamespacePayload) -> Namespace | None:
    try:
        headers = client.default_headers
        headers.update({'Accept': 'application/json'})
        res = client.post(f'v1/namespaces/{parent_namespace}/namespaces', headers=headers, data=payload.model_dump())
        data = res.json()
        return Namespace(**data)
    except Exception as e:
        print(f"Error creating namespace: {e}")
        return None

def get_namespace(client: APIClient,parent_namespace: str, namespace_uuid: str) -> Namespace:
    headers = client.default_headers
    res = client.get(f'v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}', headers=headers)
    data = res.json()
    return Namespace(**data)

def delete_namespace(client: APIClient, parent_namespace: str, namespace_uuid: str) -> bool:
    try:
        headers = client.default_headers
        res = client.delete(f'v1/namespaces/{parent_namespace}/namespaces/{namespace_uuid}', headers=headers)
        return res.status_code == 200  # Endor's API returns 200 on successful deletion
    except Exception as e:
        print(f"Error deleting namespace: {e}")
        return False

if __name__ == "__main__":
    # Note: To run this example, you need to be in the root of the project
    # and run as a module: python -m src.endor_sdk.resources.namespaces
    client = APIClient(max_retries=15, backoff_factor=1)
    client.get_openapi_spec(url=None, path="/tmp/openapiv2.swagger.json")
    
    tenant_namespace = 'endor-solutions-tgowan'

    # Create mock namespaces using Pydantic models
    mock_namespaces_to_create = [
        CreateNamespacePayload(meta=NamespaceMeta(name=f"mock-namespace-{i}", description=f"Description for mock-namespace-{i}"))
        for i in range(3)
    ]

    for payload in mock_namespaces_to_create:
        print(f"Creating namespace: {payload.meta.name}")
        created_ns = create_namespace(client, tenant_namespace, payload)
        if created_ns:
            print(f"  -> Created with UUID: {created_ns.uuid}")

    # List and delete the created namespaces
    print("\nListing all namespaces to find and delete mocks...")
    all_namespaces = list_namespaces(client, tenant_namespace)
    mock_names = {p.meta.name for p in mock_namespaces_to_create}

    for ns in all_namespaces:
        if ns.meta.name in mock_names:
            print(f"Deleting namespace: {ns.meta.name} (UUID: {ns.uuid})")
            success = delete_namespace(client, tenant_namespace, ns.uuid)
            if success:
                print("  -> Deleted successfully.")
            else:
                print("  -> Deletion failed.")
