# Follow-up Ask: Model Exposure + Third-Party KB Support

## Documentation

- [x] Create design document for ask model exposure and third-party KB integration (`docs/follow-up-model-and-kb-design.md`).
- [x] Create executable task breakdown with done/todo status.

## Backend: Data Model and Migration

- [x] Add `ask_provider_config` column to `DraftShifu` and `PublishedShifu` (JSON or TEXT JSON).
- [x] Set default empty object for `ask_provider_config` and handle legacy null values.
- [x] Generate and review Alembic migration for `ask_provider_config`.
- [x] Ensure model clone/eq/json helpers include new fields.

## Backend: DTO and Route Contract

- [ ] Extend `ShifuDetailDto` to expose ask model fields (`ask_enabled_status`, `ask_model`, `ask_temperature`, `ask_system_prompt`).
- [ ] Extend `ShifuDetailDto` to expose `ask_provider_config`.
- [ ] Update `get_shifu_draft_info` response mapping for all ask fields.
- [ ] Update `save_shifu_draft_info` signature and persistence for all ask fields.
- [ ] Update `save_shifu_detail_api` request parsing + validation for ask fields + `ask_provider_config`.
- [ ] Update swagger docs for `GET/POST /api/shifu/shifus/{shifu_bid}/detail`.

## Backend: Publish and Import/Export

- [ ] Ensure draft -> published copy path includes `ask_provider_config`.
- [ ] Extend shifu import/export payload to include `ask_provider_config`.
- [ ] Add backward-compatible defaults when imported data does not contain new fields.

## Backend: Ask Runtime Routing

- [ ] Extend `FollowUpInfo` to carry `ask_provider_config`.
- [ ] Add ask provider schema registry (provider list + json_schema + defaults).
- [ ] Add ask config metadata API (`GET /api/shifu/ask/config`) similar to TTS config style.
- [ ] Add provider adapter interface for ask KB streaming.
- [ ] Implement Dify ask provider adapter.
- [ ] Implement Coze ask provider adapter.
- [ ] Add routing in `handle_input_ask` by `ask_provider_config.provider`.
- [ ] Support mode in `ask_provider_config.mode`:
- [ ] `provider_only`
- [ ] `provider_then_llm` fallback to ask_llm
- [ ] Preserve existing ask persistence and SSE output format.
- [ ] Add timeout and fallback handling with i18n error messages.

## Backend: Configuration and Security

- [ ] Add env/config definitions for Coze credentials/endpoints.
- [ ] Add `ASK_PROVIDER_ENABLED` feature flag and default to disabled.
- [ ] Ensure provider secrets are read from env/config only (not `ask_provider_config`).

## Frontend: Shifu Settings UI

- [ ] Extend Shifu setting form schema to include ask model fields.
- [ ] Add UI controls for ask mode/model/temperature/system prompt.
- [ ] Add provider selector + mode selector and dynamic provider form by json_schema.
- [ ] Map API response -> form initial values for `ask_provider_config`.
- [ ] Map form submit -> API payload for `ask_provider_config`.
- [ ] Add frontend validation driven by provider schema.

## i18n

- [ ] Add `en-US` translation keys for new ask/provider settings labels and hints.
- [ ] Add `zh-CN` translation keys for new ask/provider settings labels and hints.
- [ ] Run translation validation scripts and fix missing keys/usages.

## Testing

- [ ] Add backend tests for shifu detail save/get with `ask_provider_config`.
- [ ] Add backend tests for ask routing by `provider` and `mode`.
- [ ] Add provider adapter unit tests (success/timeout/error).
- [ ] Add frontend tests for Shifu settings ask/provider schema-driven form behavior.
- [ ] Run relevant test suites and confirm pass.

## Quality Gates

- [ ] Run `pre-commit run`.
- [ ] Run backend targeted tests under `src/api/tests/service/shifu` and `src/api/tests/service/learn`.
- [ ] Run frontend lint/type-check for `src/cook-web`.

## Rollout

- [ ] Enable behind feature flag in non-production environment.
- [ ] Perform manual verification for Dify/Coze one by one.
- [ ] Collect logs/metrics for provider distribution and fallback rate.
- [ ] Enable in production after acceptance.
