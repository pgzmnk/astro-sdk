from astro.sql.operators.base_decorator import BaseSQLDecoratedOperator


def test_base_sql_decorated_operator_template_fields_with_parameters():
    """
    Test that parameters is in BaseSQLDecoratedOperator template_fields
     as this required for taskflow to work if XCom args are being passed via parameters.
    """
    assert "parameters" in BaseSQLDecoratedOperator.template_fields


def test_base_sql_decorated_operator_template_fields_and_template_ext_with_sql():
    """
    Test that sql is in BaseSQLDecoratedOperator template_fields and template_ext
     as this required for rending the sql in the task instance rendered section.
    """
    assert "sql" in BaseSQLDecoratedOperator.template_fields
    assert ".sql" in BaseSQLDecoratedOperator.template_ext
