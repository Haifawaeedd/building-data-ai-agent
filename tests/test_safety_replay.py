import copy
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from app import guardrails
from app.safety_replay import replay

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bundle():
    return json.loads((ROOT / 'evaluation/safety_replay/cases.json').read_text())


def test_layer_ablation_exposes_dependencies_and_false_rejection(bundle):
    result = replay(bundle)
    rows = {r['id']: r for r in result['cases']}
    assert rows['literal']['variants'] == {
        'full': 'BLOCK', 'without_lexical': 'PASS',
        'without_ast': 'BLOCK', 'without_both': 'PASS',
    }
    for case in ('unknown_table', 'unknown_column', 'system_schema'):
        assert rows[case]['blocking_layers'] == ['ast']
        assert rows[case]['variants']['without_ast'] == 'PASS'
    assert rows['write_cte']['attribution'] == 'REDUNDANT_BLOCK'
    assert rows['sleep']['full_matches_expectation'] is False
    full = result['summary']['full']
    assert (full['missed_blocks'], full['false_blocks'], full['unknown']) == (1, 1, 0)
    assert full['expected_block_cases'] == 8
    assert full['expected_pass_cases'] == 5
    assert result['sql_executed'] is False
    assert all(r['database_enforcement'] == 'NOT_TESTED' for r in result['cases'])


def test_original_pipeline_decisions_are_preserved_with_live_schema_default(bundle, monkeypatch):
    schema = types.ModuleType('app.schema')
    schema.ALLOWED_TABLES = set(bundle['schema']['allowed_tables'])
    schema.discovered_columns = set(bundle['schema']['known_columns'])
    monkeypatch.setitem(sys.modules, 'app.schema', schema)
    for row in replay(bundle)['cases']:
        allowed, _ = guardrails.validate_sql_professional(row['sql'])
        assert allowed == (row['variants']['full'] == 'PASS')


def test_report_is_reproducible_and_tracks_schema_and_input_changes(bundle):
    first = replay(bundle)
    assert first == replay(bundle)
    altered = copy.deepcopy(bundle)
    altered['schema']['known_columns'].append('imaginary')
    second = replay(altered)
    assert first['schema_sha256'] != second['schema_sha256']
    assert first['input_sha256'] != second['input_sha256']
    row = next(r for r in second['cases'] if r['id'] == 'unknown_column')
    assert row['variants']['full'] == 'PASS'


def test_validator_errors_are_unknown_not_successful_blocks(bundle, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('unexpected validator failure')
    monkeypatch.setattr(guardrails, 'validate_sql_ast', broken)
    report = replay(bundle)
    rows = {r['id']: r for r in report['cases']}
    assert rows['count']['variants']['full'] == 'UNKNOWN'
    assert rows['delete']['variants']['full'] == 'BLOCK'
    assert rows['delete']['attribution'] == 'INCOMPLETE'
    assert report['summary']['full']['evaluator_error_cases'] == 13


def test_explicit_empty_allowlist_does_not_use_live_schema(bundle):
    bundle['schema']['allowed_tables'] = []
    result = replay(bundle)
    assert next(r for r in result['cases'] if r['id'] == 'count')['variants']['full'] == 'BLOCK'


@pytest.mark.parametrize('change', ['duplicate', 'label', 'schema'])
def test_invalid_evidence_inputs_fail_instead_of_producing_metrics(bundle, change):
    if change == 'duplicate':
        bundle['cases'].append(bundle['cases'][0])
    elif change == 'label':
        bundle['cases'][0]['expected'] = 'SAFE'
    else:
        bundle['schema']['allowed_tables'] = 'all'
    with pytest.raises(ValueError):
        replay(bundle)


def test_cli_runs_without_database_model_or_network_and_surfaces_mismatches(tmp_path):
    code = '''
import runpy, socket, sys
class NoNetwork:
    def __init__(self, *args, **kwargs):
        raise AssertionError("Network access forbidden")
socket.socket = NoNetwork
sys.argv = ["replay", "evaluation/safety_replay/cases.json", "--json-output", sys.argv[1], "--fail-on-mismatch"]
try:
    runpy.run_module("app.safety_replay", run_name="__main__")
finally:
    assert "app.database" not in sys.modules
    assert "app.schema" not in sys.modules
    assert "openai" not in sys.modules
'''
    output = tmp_path / 'report.json'
    result = subprocess.run([sys.executable, '-c', code, str(output)], cwd=ROOT,
                            text=True, capture_output=True)
    assert result.returncode == 1, result.stderr
    assert not result.stderr
    assert json.loads(output.read_text())['summary']['full']['false_blocks'] == 1
