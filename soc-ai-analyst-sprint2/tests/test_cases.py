import json
from copy import deepcopy
from dataclasses import replace
from uuid import UUID

import pytest

from tests.helpers import add_enrichment, assert_rejected, make_case

URL = "/api/v1/cases"


@pytest.mark.parametrize("source", ["elastic", "wazuh"])
def test_accept_valid_origin(client, application, id_factory, source):
    payload = make_case(source)
    response = client.post(URL, json=payload)
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "accepted"
    assert UUID(result["case_id"]).version == 4
    assert result["submitted_case_id"] == payload["case_id"]
    assert result["case_id"] != payload["case_id"]
    id_factory.assert_called_once()
    stored = application.state.case_service.store.get(payload["case_id"])
    assert stored.submitted_case.model_dump(exclude_unset=True) == payload


def test_two_cases_have_different_uuid4_ids(client):
    first = client.post(URL, json=make_case(case_id="INC-A")).json()
    second = client.post(URL, json=make_case(case_id="INC-B")).json()
    assert first["case_id"] != second["case_id"]
    assert UUID(first["case_id"]).version == UUID(second["case_id"]).version == 4


def test_mixed_case_with_custom_fields_is_preserved(client, application):
    payload = make_case()
    wazuh = make_case("wazuh")["alerts"][0]
    wazuh.update(alert_id="w-unique", raw_alert={"id": "w-unique"})
    payload["alerts"].append(wazuh)
    payload["alerts"][0]["raw_alert"].update(
        {"custom.rule": {"payload": [None, True, 7, 1.5, "text"]}}
    )
    wazuh["raw_alert"]["decoder"] = {"name": "synthetic_custom_decoder"}
    payload["correlation"] = {"fields": ["user", "custom.indicator"]}
    payload["title"] = ""
    payload["description"] = "Synthetic mixed case"
    add_enrichment(payload)
    original = deepcopy(payload)
    response = client.post(URL, json=payload)
    assert response.status_code == 201, response.text
    store = application.state.case_service.store
    saved = store.get(payload["case_id"])
    assert saved.submitted_case.model_dump(exclude_unset=True) == original
    # Mutating a returned copy must not mutate accepted evidence.
    saved.submitted_case.alerts[0].raw_alert.clear()
    assert (
        store.get(payload["case_id"]).submitted_case.model_dump(exclude_unset=True)
        == original
    )


def test_same_alert_can_belong_to_different_cases(client):
    assert client.post(URL, json=make_case(case_id="A")).status_code == 201
    assert client.post(URL, json=make_case(case_id="B")).status_code == 201


def test_duplicate_submitted_id_is_conflict_without_new_uuid(client, id_factory):
    payload = make_case()
    assert client.post(URL, json=payload).status_code == 201
    response = client.post(URL, json=payload)
    assert response.status_code == 409
    assert response.json()["detail"][0]["rule"] == "VR-04"
    assert "case_id" not in response.json()
    assert id_factory.call_count == 1


@pytest.mark.parametrize(
    ("field", "rule"),
    [
        ("schema_version", "VR-01"),
        ("case_id", "VR-03"),
        ("submitted_at", "VR-05"),
        ("alerts", "VR-06"),
    ],
)
def test_missing_top_level_field(client, id_factory, field, rule):
    payload = make_case()
    del payload[field]
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    ("field", "rule"),
    [("alert_id", "VR-09"), ("source_system", "VR-12"), ("raw_alert", "VR-15")],
)
def test_missing_alert_field(client, id_factory, field, rule):
    payload = make_case()
    del payload["alerts"][0][field]
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    ("field", "value", "rule"),
    [
        ("schema_version", "2.0", "VR-02"),
        ("schema_version", 1.0, "VR-02"),
        ("case_id", 123, "VR-03"),
        ("case_id", " \t", "VR-03"),
        ("alerts", [], "VR-07"),
        ("alerts", {}, "VR-06"),
        ("title", 123, "CONTRACT"),
        ("enrichments", {}, "VR-21"),
    ],
)
def test_invalid_top_level_values(client, id_factory, field, value, rule):
    payload = make_case()
    payload[field] = value
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    ("field", "value", "rule"),
    [
        ("alert_id", 1, "VR-09"),
        ("alert_id", "", "VR-09"),
        ("source_system", "splunk", "VR-13"),
        ("source_system", "Elastic", "VR-13"),
        ("raw_alert", {}, "VR-16"),
        ("raw_alert", [], "VR-16"),
        ("raw_alert", "native-text", "VR-16"),
        ("source_version", "latest", "VR-19"),
        ("ecs_version", 8, "VR-20"),
    ],
)
def test_invalid_alert_values(client, id_factory, field, value, rule):
    payload = make_case()
    payload["alerts"][0][field] = value
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    "timestamp",
    [
        "yesterday",
        "2026-02-30T20:30:00Z",
        "2026-09-29",
        "2026-09-29T20:30:00",
        "2026-09-29 20:30:00Z",
        1790713800,
        True,
    ],
)
def test_invalid_timestamp(client, id_factory, timestamp):
    payload = make_case()
    payload["submitted_at"] = timestamp
    assert_rejected(client.post(URL, json=payload), id_factory, "VR-05")


@pytest.mark.parametrize(
    "timestamp", ["2026-09-29T15:30:00-05:00", "2026-09-29t20:30:00.123z"]
)
def test_valid_timezone_and_fractional_timestamp(client, timestamp):
    payload = make_case()
    payload["submitted_at"] = timestamp
    assert client.post(URL, json=payload).status_code == 201


@pytest.mark.parametrize("count,expected", [(50, 201), (51, 422)])
def test_initial_alert_limit(client, id_factory, count, expected):
    response = client.post(URL, json=make_case(count=count))
    assert response.status_code == expected
    if expected == 422:
        assert_rejected(response, id_factory, "VR-08")


def test_duplicate_alert_ids_rejected_even_across_sources(client, id_factory):
    payload = make_case()
    payload["alerts"].extend(make_case("wazuh")["alerts"])
    assert_rejected(client.post(URL, json=payload), id_factory, "VR-11")


@pytest.mark.parametrize(
    "raw", [{"event": {"id": "different"}}, {"anything": True}, {"event": {"id": 1}}]
)
def test_native_identifier_provenance(client, id_factory, raw):
    payload = make_case()
    payload["alerts"][0]["raw_alert"] = raw
    assert_rejected(client.post(URL, json=payload), id_factory, "VR-10")


@pytest.mark.parametrize(
    ("pointer", "raw"),
    [
        (
            "/kibana.alert.uuid",
            {"kibana.alert.uuid": "native-0", "event": {"id": "original-event"}},
        ),
        (
            "/_id",
            {"_id": "native-0", "_index": "synthetic", "_source": {"custom": True}},
        ),
        ("/ids/0/value", {"ids": [{"value": "native-0"}]}),
        ("/id~1value~0", {"id/value~": "native-0"}),
    ],
)
def test_configured_id_pointer_supports_other_export_shapes(
    client, application, pointer, raw
):
    service = application.state.case_service
    service.settings = replace(service.settings, elastic_alert_id_pointer=pointer)
    payload = make_case()
    payload["alerts"][0]["raw_alert"] = raw
    assert client.post(URL, json=payload).status_code == 201


@pytest.mark.parametrize(
    ("source", "version", "ecs"),
    [
        ("elastic", "8.19", "8.x"),
        ("elastic", "8.19.4", "8.17.0"),
        ("elastic", "9.4", "8.17"),
        ("wazuh", "4.14.1", None),
    ],
)
def test_supported_versions(client, source, version, ecs):
    payload = make_case(source)
    payload["alerts"][0]["source_version"] = version
    if ecs is not None:
        payload["alerts"][0]["ecs_version"] = ecs
    assert client.post(URL, json=payload).status_code == 201


@pytest.mark.parametrize(
    ("source", "field", "value", "rule"),
    [
        ("wazuh", "source_version", "8.19", "VR-19"),
        ("elastic", "source_version", "4.14", "VR-19"),
        ("elastic", "source_version", "8.20", "VR-19"),
        ("elastic", "ecs_version", "9.x", "VR-20"),
    ],
)
def test_semantically_unsupported_versions(
    client, id_factory, source, field, value, rule
):
    payload = make_case(source)
    payload["alerts"][0][field] = value
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    "field,suffix,rule",
    [("source_version", ".19", "VR-19"), ("ecs_version", ".x", "VR-20")],
)
def test_very_large_version_component_returns_validation_error(
    client, id_factory, field, suffix, rule
):
    payload = make_case()
    payload["alerts"][0][field] = "9" * 5000 + suffix
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    "location", ["case", "alert", "correlation", "enrichment", "observable"]
)
def test_unknown_project_defined_properties_are_rejected(client, id_factory, location):
    payload = make_case()
    payload["correlation"] = {"fields": ["user"]}
    add_enrichment(payload)
    target = {
        "case": payload,
        "alert": payload["alerts"][0],
        "correlation": payload["correlation"],
        "enrichment": payload["enrichments"][0],
        "observable": payload["enrichments"][0]["observable"],
    }[location]
    target["unexpected"] = True
    assert_rejected(client.post(URL, json=payload), id_factory, "CONTRACT")


@pytest.mark.parametrize(
    "field", ["title", "description", "correlation", "enrichments"]
)
def test_explicit_null_optional_case_fields_are_rejected(client, id_factory, field):
    payload = make_case()
    payload[field] = None
    rule = "VR-21" if field == "enrichments" else "CONTRACT"
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    "field,rule", [("source_version", "VR-19"), ("ecs_version", "VR-20")]
)
def test_explicit_null_optional_alert_fields_are_rejected(
    client, id_factory, field, rule
):
    payload = make_case()
    payload["alerts"][0][field] = None
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    "metadata", [{}, {"fields": []}, {"fields": ["user", "user"]}, {"fields": [" "]}]
)
def test_invalid_correlation_metadata(client, id_factory, metadata):
    payload = make_case()
    payload["correlation"] = metadata
    assert_rejected(client.post(URL, json=payload), id_factory, "CONTRACT")


@pytest.mark.parametrize("field", ["provider", "observable"])
def test_missing_enrichment_fields(client, id_factory, field):
    payload = make_case()
    add_enrichment(payload)
    del payload["enrichments"][0][field]
    response = client.post(URL, json=payload)
    assert_rejected(response, id_factory, "VR-22")
    assert response.json()["detail"][0]["loc"] == ["body", "enrichments", 0, field]


@pytest.mark.parametrize("field", ["related_alert_ids", "raw_result"])
def test_explicit_null_optional_enrichment_fields_are_rejected(
    client, id_factory, field
):
    payload = make_case()
    add_enrichment(payload)
    payload["enrichments"][0][field] = None
    assert_rejected(client.post(URL, json=payload), id_factory, "CONTRACT")


@pytest.mark.parametrize(
    "references,rule",
    [(["missing"], "VR-23"), ([], "CONTRACT"), (["native-0", "native-0"], "CONTRACT")],
)
def test_invalid_enrichment_references(client, id_factory, references, rule):
    payload = make_case()
    add_enrichment(payload)
    payload["enrichments"][0]["related_alert_ids"] = references
    assert_rejected(client.post(URL, json=payload), id_factory, rule)


@pytest.mark.parametrize(
    "body,rule",
    [("{", "JSON"), ("[]", "CONTRACT"), ("null", "CONTRACT"), ("42", "CONTRACT")],
)
def test_malformed_json_or_non_object_body(client, id_factory, body, rule):
    response = client.post(
        URL, content=body, headers={"Content-Type": "application/json"}
    )
    assert_rejected(response, id_factory, rule)


@pytest.mark.parametrize("bad_number", [float("nan"), float("inf"), -float("inf")])
def test_non_json_numeric_constants_are_rejected(client, id_factory, bad_number):
    payload = make_case()
    payload["alerts"][0]["raw_alert"]["bad"] = bad_number
    response = client.post(
        URL, content=json.dumps(payload), headers={"Content-Type": "application/json"}
    )
    assert_rejected(response, id_factory, "VR-16")


def test_invalid_case_does_not_reserve_submitted_id(client, id_factory):
    payload = make_case()
    payload["alerts"][0]["alert_id"] = "mismatch"
    assert_rejected(client.post(URL, json=payload), id_factory, "VR-10")
    assert client.post(URL, json=make_case()).status_code == 201


def test_openapi_documents_intake_and_initial_limit(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][URL]["post"]
    assert set(operation["responses"]) >= {"201", "409", "422"}
    model = schema["components"]["schemas"]["IncidentCase"]
    assert model["properties"]["alerts"]["maxItems"] == 50
    assert set(model["required"]) == {
        "schema_version",
        "case_id",
        "submitted_at",
        "alerts",
    }
