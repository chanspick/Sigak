"""SIGAK Pydantic schemas — application-level JSONB validation.

All JSONB columns in user_profiles / conversations have no DB-level constraint.
Shape is guaranteed by Pydantic v2 models in this package.
Read path:  DB JSONB dict → Model.model_validate(dict)
Write path: Model(...) → .model_dump(mode="json") → INSERT/UPDATE

See SPEC-ONBOARDING-V2 §11 (REQ-SCHEMA-001~004) and design doc §5-6.
"""
