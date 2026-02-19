# 05 - Security (MVP)

Server-side controls:
- Only SELECT allowed
- Single statement only
- No semicolons
- Tables restricted to ALLOWED_TABLE_1 and ALLOWED_TABLE_2

Next steps:
- Create a DB role with permissions only on the 2 tables
- Enforce RLS if exposing user-specific data
