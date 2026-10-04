"""
The committed OpenAPI document the web generates its types from must equal what the
API exports now. When it differs, run `python -m centinela_api.contrato`.
"""
import json

from centinela_api.contrato import DESTINO, esquema


def test_the_committed_openapi_document_equals_the_one_the_api_exports():
    exportado = json.dumps(esquema(), indent=2, sort_keys=True) + "\n"
    assert DESTINO.read_text() == exportado, (
        f"{DESTINO} differs from the API's OpenAPI document; run `python -m centinela_api.contrato` and commit it"
    )
