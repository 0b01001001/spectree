# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Support msgspec as another model adapter (#479)
- Add changelog, prepare v3
- Add changelog cmd to makefile

### Changed

- Start to replace pydantic with dataclass (#468)
- Bump the all-actions group with 2 updates (#469)
- Introduce the model adaptive layer (#476)
- Use `uv` pkg ecosystem in dependabot (#477)
- Bump actions/upload-pages-artifact from 4 to 5 in the all-actions group (#478)
- Bump the all-pips group across 1 directory with 5 updates (#480)
- Bump python-multipart from 0.0.26 to 0.0.27 (#481)

## [2.0.1] - 2025-12-15

### Changed

- Bump actions/checkout from 5 to 6 in the all-actions group (#463)

### Fixed

- Redoc cdn (#466)
- Dump spec as a JSON (#467)

## [2.0.0] - 2025-11-30

### Changed

- Prepare for the v2 formal release (#462)

## [2.0.0a1] - 2025-11-10

### Added

- Add free threading classifier to pyproject (#456)
- Add option to keep serialized response (#459)

### Changed

- Bump the all-actions group with 2 updates (#457)
- Release v2.0.0a1 (#460)

## [2.0.0a0] - 2025-10-22

### Changed

- Drop pydantic v1, drop py3.9, add py3.14 (#455)

## [1.5.8] - 2025-10-02

### Changed

- Use validation/serialization mode for pydantic v2 schemas (#453)
- Bump version (#454)

## [1.5.7] - 2025-09-18

### Changed

- Bump version

### Fixed

- Use pipe for falcon stream, run async read/write in the event loop (#451)

## [1.5.6] - 2025-09-17

### Fixed

- Quart async test (#450)

## [1.5.5] - 2025-09-12

### Changed

- Bump the all-actions group with 2 updates (#444)

### Fixed

- Use the SPDX license expression in pyproject (#443)
- Falcon json get_media should not throw error if json is annotated (#447)

## [1.5.4] - 2025-08-30

### Changed

- Use validation errors instead of json (#442)

### Fixed

- Use pylock file to guarantee pydantic v1&v2 env (#439)

## [1.5.3] - 2025-08-27

### Added

- Support enum value in naive deep copy (#438)

### Changed

- Replace pre-commit with prek (#436)

### Fixed

- Keep the falcon file stream in memory (#435)

## [1.5.2] - 2025-08-22

### Fixed

- Falcon form with `application/x-www-form-urlencoded` (#434)

## [1.5.1] - 2025-08-22

### Fixed

- Check the filename to determine if the falcon bodypart is a file (#433)

## [1.5.0] - 2025-08-22

### Changed

- Bump offapi to avoid deprecated warnings (#432)

### Fixed

- Annotate with the dedicated file type for differente web frameworks (#431)

## [1.4.12] - 2025-08-19

### Fixed

- Convert ±inf/nan in openapi schema to str format (#429)

## [1.4.11] - 2025-06-26

### Changed

- Use falcon http_status_to_code directly (#423)
- Combine flask & quart duplicate parts (#425)

### Fixed

- Tuple response handling for flask (#424)

## [1.4.10] - 2025-06-19

### Changed

- Merge the duplicate code in falcon response validation (#422)

### Fixed

- Correctly serialize dates, uuids, and other data types supported by Pydantic (#421)

## [1.4.9] - 2025-06-03

### Changed

- Bump to version 1.4.9, add code owner (#419)

### Fixed

- Set required field on requestBody according to OpenAPI spec (#418)

## [1.4.8] - 2025-05-23

### Changed

- Bump to version 1.4.8 (#417)

### Fixed

- Allow repeated header keys for flask response (#416)

## [1.4.7] - 2025-04-27

### Changed

- Bump astral-sh/setup-uv from 5 to 6 (#410)
- Change dependency groups monthly (#411)
- Perf (flask): get annotations when no validation error and use cache for type hints (#412)
- Cache type hints for other web frameworks (#413)

## [1.4.6] - 2025-04-10

### Changed

- Adopt uv (#409)

### Fixed

- Conversion to dictionary depending on pydantic version (#408)

## [1.4.5] - 2025-03-04

### Changed

- Skip websocket route in generated spec (#405)

### Fixed

- Skip websocket for quart (#406)
- Avoid missing websocket attribute if werkzeug < v1 (#407)

## [1.4.4] - 2025-01-06

### Added

- Support `spectree[offline]` (#399)

## [1.4.3] - 2024-12-31

### Added

- Support user custom error (#398)

### Changed

- Switch to OIDC release (#394)

### Fixed

- Flask crashes after Pydantic V2 validator raises ValueError + compatibility issue in default_after_handler (#397)

## [1.4.2] - 2024-12-13

### Added

- Add sitemap and robots (#391)

### Changed

- Display global config details (#390)
- Maintain pydantic.v1 model compatibility while using pydantic v2 (#393)

## [1.4.1] - 2024-11-25

### Changed

- Enable 3.13 test, deprecate 3.8 (#389)

### Fixed

- Make it compatible with pydantic v1 & v2 (#388)

## [1.4.0] - 2024-11-24

### Added

- Add skipping openapi endpoints to howto
- Support pydantic v1 & v2 through Protocol (#387)

## [1.3.0] - 2024-11-24

### Changed

- Skip validation for request & response (#383)

## [1.2.11] - 2024-10-31

### Changed

- Set cookie secure (#377)
- Fixes #350 - keyword with no conflict in alias (#380)
- Fix for openapi.json location if another root directory (#378)
- Bump version

### Fixed

- Fix secure alert about set_cookie (#376)
- Fix the quart dependency in pyproject toml file (#381)

## [1.2.10] - 2024-06-18

### Added

- Add scalar ui in readme

### Changed

- Update pytest requirement from ~=7.1 to >=7.1,<9.0 (#371)
- Bump actions/configure-pages from 4 to 5 (#372)
- Keep track of resp_validation_error in flask plugin (#373)

### Fixed

- Assign the resp_validation_err (#375)

## [1.2.9] - 2024-01-26

### Added

- Add scalar openapi ui, update swagger version to 5 (#369)

### Changed

- Bump actions/setup-python from 4 to 5 (#362)
- Bump actions/configure-pages from 3 to 4 (#363)
- Bump actions/deploy-pages from 2 to 3 (#364)
- Bump github/codeql-action from 2 to 3 (#365)
- Bump actions/upload-pages-artifact from 2 to 3 (#367)
- Bump actions/deploy-pages from 3 to 4 (#366)
- Introduce defspec in readme (#370)

## [1.2.8] - 2023-11-07

### Added

- Add py 3.12 test in ci (#358)
- Add returning result in falcon decorator (#356)

### Changed

- Adopt ruff (#359)
- Bump version (#360)

## [1.2.7] - 2023-10-27

### Fixed

- Flask query list items (#357)

## [1.2.6] - 2023-10-07

### Changed

- Use set directly for the secuirity scheme requirements (#351)

### Fixed

- Return original resp when no basemodel found in the resp (#353)

## [1.2.5] - 2023-10-02

### Fixed

- Flask mimetype check (#349)

## [1.2.4] - 2023-09-25

### Added

- Added more Flask `make_response` tests && added headers usage during response generation (#344)

### Fixed

- Flask & quart resp validation (#345)

## [1.2.3] - 2023-09-22

### Changed

- Fix Flask status code processing after release 1.2.2 (#341)
- Update ci python version (#342)
- Bump version (#343)

## [1.2.2] - 2023-09-21

### Changed

- Bump actions/checkout from 3 to 4 (#337)
- [Proposal] Support Pydantic root model responses (#338)
- Unify response validation (#339)
- Bump version (#340)

## [1.2.1] - 2023-08-16

### Added

- Add doc config for og, sponsor, etc (#333)
- Support returning lists of unserialized models (#335)

### Changed

- Update pydantic v2 usage in readme (#331)
- Use myst-parser and shibuya theme (#332)
- Release 1.2.1 (#336)

### Fixed

- Fix doc css (#334)

## [1.2.0] - 2023-07-18

### Added

- Support Pydantic v2 with v1 backport (#326)
- Add pydantic v1&v2 test (#327)

### Changed

- Bump actions/upload-pages-artifact from 1 to 2 (#325)

## [1.1.5] - 2023-07-03

### Fixed

- Freeze pydantic to <2 (#321)

## [1.1.4] - 2023-07-01

### Added

- Add readthedoc support (#315)
- Added more information about deprecated endpoint to README (#316)

### Fixed

- Fix pydantic to <2 (#318)

## [1.1.3] - 2023-05-30

### Changed

- Clean test warnings (#308)
- Extract the logic for getting the operation_id to a plugin method (#313)
- Release 1.1.3 (#314)

## [1.1.2] - 2023-04-24

### Added

- Add Support for customizing how nested names are generated (#305)
- Add github issue and feature request templates (#306)

## [1.1.1] - 2023-04-23

### Added

- Add test for top-level json list, use syrupy snapshot (#293)

### Changed

- Bump actions/deploy-pages from 1 to 2 (#295)
- Check presence of media before attempting to parse it (#296)
- Updated contributing docs and added pre-commit requirement. (#298)
- Refactor the get_model_key util function (#302)

### Fixed

- Use the status code from std http lib (#303)

## [1.1.0] - 2023-03-10

### Added

- Add envd dev env, upgrade black (#288)
- Add py.typed file (#289)

### Changed

- Bump actions/configure-pages from 2 to 3 (#286)
- Replace the codeql badge (#290)

### Fixed

- Fix flask test context (#284)

## [1.0.3] - 2022-11-29

### Changed

- Update flake8 requirement from <6,>=4 to >=4,<7 (#278)
- Update autoflake requirement from ~=1.4 to >=1.4,<3.0 (#279)
- Allow endpoints to override its operationId (#281)
- Release 1.0.3 (#282)

## [1.0.2] - 2022-11-19

### Changed

- Initial version (#259) (#260)
- Change to pyproject (#265)

### Fixed

- Fix starlette cookie in test client (#277)

## [1.0.1] - 2022-11-09

### Changed

- Release v1

## [1.0.0a4] - 2022-11-09

### Added

- Add CodeQL workflow for GitHub code scanning (#272)

### Changed

- AND/OR root security configuration (#269)

### Fixed

- Only call `after` at the end of the validation (#274)

## [1.0.0a3] - 2022-10-18

### Added

- Add quart demo to readme (#268)

### Changed

- Dmitry/quart plugin (#262)

## [1.0.0a2] - 2022-10-15

### Changed

- Create FUNDING.yml
- Move mypy config to setup.cfg (#256)
- Replace slash from generated operationId (#264)
- Import plugin using import_module (#266)
- Update ci (#267)

## [1.0.0a1] - 2022-08-24

### Changed

- Merge branch 'master' into yed/form-data-support
- Merge pull request #225 from yedpodtrzitko/yed/form-data-support
- Update flake8 requirement from ~=4.0 to >=4,<6
- Merge pull request #252 from 0b01001001/dependabot/pip/flake8-gte-4-and-lt-6
- Use typing.get_type_hints instead of .__annotations__
- Make format
- Merge pull request #250 from DisruptiveLabs/use_get_type_hints

### Fixed

- Fix rest annotations in test (#253)
- __root__ properties (#255)

## [1.0.0a0] - 2022-08-01

### Added

- Add bound for werkzeug dependency due to breaking change (#241)
- Added form-data support
- Added multipart/form-data support for falcon-asgi, updated demos, minor changes
- Add copy of `werkzeug.parse_rule` which is now marked as internal (#244)

### Changed

- Drop support for Falcon 2 (#239)
- Finish form data support
- Prerelease of 1.0.0a0 (#245)

### Fixed

- Use mypy.ignore_missing_imports instead of suppressing them everywhere manually (#238)

## [0.10.3] - 2022-07-14

### Changed

- Make email-validator an optional dependency (#236)
- Update setup.py

## [0.10.2] - 2022-07-07

### Changed

- Create dependabot.yml (#230)
- Bump actions/setup-python from 2 to 4 (#231)
- Upgrade Swagger UI to v4 (#234)
- Update setup.py

### Fixed

- Log the validation error in the default  handler (#233)

## [0.10.1] - 2022-06-13

### Added

- Add trailing slash to apidoc routes (#224)

### Changed

- Use 'furo' as the new doc theme (#223)
- Define flask tests in single place and reuse them (#227)
- Release 0.10.1

### Fixed

- Dont validate JSON data in request which cant provide it (#228)

## [0.10.0] - 2022-05-04

### Changed

- Release 0.10.0

## [0.10.0a1] - 2022-05-01

### Added

- Support list resp with List[Model] (#222)

## [0.9.2] - 2022-04-26

### Added

- Update readme: add pydantic instance response (#218)

### Changed

- Fix falcon async test (#221)

### Fixed

- Fix falcon plugin (#220)

## [0.9.1] - 2022-04-24

### Changed

- 0.9.1 (#217)

### Fixed

- Handle case when no view response is defined (#216)

## [0.9.0] - 2022-04-24

### Added

- Support skipping validation and returning models (#212)

### Changed

- Use hash suffix instead of prefix in get_model_key (#214)
- Release 0.9.0 (#215)

## [0.8.0] - 2022-04-17

### Added

- Add type hint (#210)

### Changed

- Change to checkout@v3 (#209)
- Release 0.8.0 (#211)

## [0.7.6] - 2022-02-22

### Added

- Add description argument to Response.add_model() (#206)
- Add doc for `Response` (#207)

## [0.7.5] - 2022-02-21

### Fixed

- Fix flask ImmutableMultiDict and EnvironHeaders parser (#205)

## [0.7.4] - 2022-02-17

### Changed

- Refact build (#201)

### Fixed

- Fix req + args parse in starlette (#203)

## [0.7.3] - 2022-02-10

### Added

- Add flask blueprint spec path test (#197)

### Changed

- Restored docstring paragraph formatting (#199)
- Upgrade dev version (#200)

## [0.7.2] - 2022-01-26

### Changed

- Fix blueprint find_routes method (#193)
- Fix swagger oauth2 redirect (#196)

## [0.7.1] - 2022-01-08

### Changed

- Fix terms of service case (#192)

## [0.7.0] - 2022-01-06

### Added

- Add openapi info (#190)
- Add config doc (#191)

### Changed

- Log format (#184)
- Upgrade actions (#188)

## [0.6.8] - 2021-11-17

### Added

- Add option to specify custom descriptions for response status codes. (#182)

### Changed

- Release 0.6.8

## [0.6.7] - 2021-11-06

### Added

- Add option to describe path parameters (#181)

### Changed

- Release 0.6.7

## [0.6.6] - 2021-11-04

### Added

- Support py3.10 (#179)
- Add option for using custom page templates (#180)
- Update readme: add customized template page

### Changed

- Release 0.6.6

## [0.6.5] - 2021-11-03

### Added

- Add option for custom validation error status (#178)

### Changed

- Fold the security example
- Listen to grammarly
- Release 0.6.5

## [0.6.4] - 2021-10-26

### Added

- Add support for parsing complex function docstings. (#175)

### Changed

- Update bearerFormat from dict to str (#172)

### Fixed

- Fix falcon3 media exception (#174)

## [0.6.3] - 2021-09-23

### Changed

- Ability to mark an endpoint as deprecated
- Merge pull request #170 from Vlczech/deprecated_endpoint
- Release 0.6.3 (#171)

## [0.6.2] - 2021-09-22

### Changed

- Merge pull request #167 from 0b01001001/fix-issue-166
- Fixed structural error in OAS
- Merge pull request #168 from Vlczech/fix_servers_emptyfields
- Release 0.6.2 (#169)

### Fixed

- Fix issue 166

## [0.6.1] - 2021-07-27

### Changed

- Release 0.6.1 (#163)

### Fixed

- Fix security AND/OR (#162)

## [0.6.0] - 2021-06-30

### Changed

- Falcon ASGI support (#46)
- Release 0.6.0
- Merge pull request #157 from 0b01001001/release

## [0.5.4] - 2021-06-29

### Changed

- Security & security_schemes described in README
- Merge pull request #151 from Vlczech/patch-1
- Servers definition
- Merge pull request #153 from 0b01001001/fix/security
- Merge branch 'master' into servers_definition
- Merge pull request #154 from Vlczech/servers_definition
- Release 0.5.4
- Merge pull request #156 from 0b01001001/release

### Fixed

- Fix security

## [0.5.3] - 2021-06-16

### Changed

- Global security and some changes in security
- Merge pull request #149 from Vlczech/security_global
- Release 0.5.3
- Merge pull request #150 from 0b01001001/release

## [0.5.2] - 2021-06-04

### Changed

- Empty path enpoints leads to Semantic error => clean all empty paths
- Merge pull request #145 from Vlczech/fix_empty_enpoint_path
- Squashed commit of the following:
- Release 0.5.2
- Merge pull request #147 from 0b01001001/release
- Code structure (paths) leaking => short hash used instead (#146)

## [0.5.1] - 2021-06-02

### Changed

- "securityScheme: null" leads to Structural error (should be object)
- Fix Falcon3 compatibility issue on GET endpoints
- Merge pull request #137 from mortymacs/falcon3-compatibility-fix
- Fix Falcon2 and 3 compatibility issue
- Merge pull request #138 from mortymacs/falcon3-compatibility-fix
- Merge remote-tracking branch 'master' into fix_securityschemes
- Merge pull request #140 from Vlczech/fix_securityschemes
- Update makefile: test falcon 2 and 3
- Merge pull request #142 from 0b01001001/falcon_test
- Merge pull request #143 from 0b01001001/falcon_bypass
- Release 0.5.1
- Merge pull request #144 from 0b01001001/release

### Fixed

- Fix falcon bypass for 2 & 3

## [0.5.0] - 2021-05-27

### Added

- Add Authentication and Authorization logic. (#127)

### Changed

- Merge pull request #128 from greyli/simplify-if
- Merge pull request #130 from O1dLiu/fix_model_name_unique
- Deepcopy schema
- Merge pull request #133 from 0b01001001/dev
- Release 0.5.0
- Merge pull request #134 from 0b01001001/dev

### Fixed

- Fix form model overwritten
- Fix flask filter
- Fix test definition
- Fix nested definition
- Fix lint

### Removed

- Remove unnecessary if statements

## [0.4.3] - 2021-04-24

### Added

- Support OpenAPI tag object (#122)

### Changed

- Release 0.4.3
- Merge pull request #123 from 0b01001001/dev

## [0.4.2] - 2021-04-07

### Changed

- Merge pull request #114 from jonathanlintott/fix-any-converter-spec
- Merge pull request #116 from 0b01001001/dev
- Catch route parameter keywords from schema when parsing params
- Merge pull request #115 from jonathanlintott/allow-extra-keywords
- Release 0.4.2
- Merge pull request #117 from 0b01001001/dev

### Fixed

- Fix flask any converter produced spec
- Fix falcon example
- Fix falcon 3
- Fix falcon demo JSON formatter super init
- Fix falcon App/API warning, fix header text/plain

## [0.4.1] - 2021-03-21

### Changed

- Update readme
- Merge pull request #105 from FerdinandZhong/master
- Possibility to set description in OAS
- Merge pull request #108 from Vlczech/info_description
- Parse from raw
- Release 0.4.1
- Merge pull request #112 from 0b01001001/dev

## [0.4.0] - 2021-01-15

### Added

- Support flask view
- Support flask restful plugin
- Add example for type annotation in README
- Add flask view test

### Changed

- Redoc ui fix
- Merge pull request #99 from yoursvivek/redoc-ui-fix
- Pre-commit hooks for git
- Use flake 8 in pre-commit as well.
- Merge pull request #101 from yoursvivek/pre-commit
- For flask use current_app (recommended way)
- Don't enforce flask install on starlette/falcon users
- Cache spec to run tests without flask app_context
- Merge pull request #102 from yoursvivek/flask_current_app_context
- Merge branch 'master' into dev
- Enable function annotation based type detection
- Merge pull request #100 from yoursvivek/annotation
- Merge branch 'master' into dev
- Release 0.4.0
- Merge pull request #104 from 0b01001001/dev

### Fixed

- Fix flask blueprint tests

## [0.3.16] - 2020-12-11

### Changed

- Merge pull request #95 from 0b01001001/dev

## [0.3.15] - 2020-12-11

### Changed

- Merge pull request #93 from 0b01001001/dev

## [0.3.14] - 2020-12-09

### Changed

- Merge pull request #89 from 0b01001001/dev
- Merge pull request #90 from 0b01001001/dev

## [0.3.13] - 2020-12-08

### Changed

- Merge pull request #86 from 0b01001001/dev

## [0.3.12] - 2020-11-18

### Added

- Support flask x-www-form-urlencoded
- Support flask multipart/form-data
- Support pypy
- Add __root__ test

### Changed

- Format
- Release v0.3.12
- Release v0.3.13
- Split lint and test, add py3.9
- Release v0.3.14
- Fix openapi >=3 versions compatibility (#91)
- Release v0.3.15
- Ignore E203 W503
- Use parse_obj instead of validate
- Release v0.3.16
- Use github action account for actions
- Merge pull request #81 from 0b01001001/dev
- Merge pull request #84 from 0b01001001/dev

### Fixed

- Fix conflicts
- Fix black version
- Fix starlette dependencies
- Fix test
- Fix E501

## [0.3.11] - 2020-11-03

### Added

- Add 422 default model (#57)

### Changed

- Release v0.3.10 (#77)
- Merge branch 'master' into dev
- Format code
- V0.3.11 add 422 validation model (#80)

### Fixed

- Fix 422 description (#79)

## [0.3.10] - 2020-10-26

### Added

- Add operationId test

### Changed

- Merge pull request #76 from 0b01001001/dev
- Fixes for operationId, flask/get_json() and more unique path name (#70)
- Release v0.3.10

### Removed

- Remove pages for merge requests

## [0.3.9] - 2020-10-23

### Changed

- Merge pull request #62 from 0b01001001/dev
- Merge pull request #64 from 0b01001001/dev
- Create python-publish.yml
- Create pythondoc.yml
- Update pythondoc.yml
- Merge remote-tracking branch 'origin' into dev
- Merge pull request #65 from 0b01001001/dev
- Release v0.3.9
- Merge pull request #68 from 0b01001001/dev

### Fixed

- Fix starlette static file bug

## [0.3.7] - 2020-10-06

### Added

- Add CI for PR to dev branch
- Add default value and example to demo
- Add config
- Add default handlers for before and after
- Add docs for handlers
- Add handler to spectree init part
- Add handler to framework validation part
- Support specific endpoint handler to overwrite the global one
- Add flask before after handler test
- Add falcon before and after handler test
- Add starlette before and after handler test
- Add flask Blueprint support
- Add Blueprint url_prefix test case
- Add flake8 quotes check
- Add description to the upper level
- Add test for description

### Changed

- Change to pydantic model parse_obj
- Update redoc HTML
- Upgrade to v0.3.5
- Merge pull request #49 from 0b01001001/dev
- Change tags to immutable tuple from mutable list
- Reformat code
- Use qualname instead of repr for starlette func/method
- Update readme: before&after
- Upgrade to v0.3.6
- Merge pull request #52 from 0b01001001/dev
- Merge pull request #59 from hkwi/flask_blueprint
- Format code
- Release v0.3.7
- Format quote
- Stop build when there is any flake8 error
- Upgrade to v0.3.8
- Use ASYNC to identify async framework
- Use GitHub pages
- Merge pull request #61 from 0b01001001/dev

### Fixed

- Fix query: unwrap schema
- Fix workflow
- Fix typo

### Removed

- Remove current_app

## [0.3.3] - 2020-03-18

### Added

- Add headers check in spec
- Update readme: add falcon demo and starlette demo
- Add functional test for summary and description
- Add other methods in class
- Add failing test for starlette mounts.
- Add test for starlette endpoint, delete pop_keywords
- Add test for starlette endpoint, delete pop_keywords
- Add check to makefile as default one, so `make` can help check coding style and test
- Add log when validation failed
- Update falcon example: add logging
- Add backend arg to SpecTree
- Add test and doc for customized backend
- Add req validatation to falcon and starlette

### Changed

- Use root_validator to convert headers keys into lower cases
- Update readme faq: use root_validator
- Merge pull request #17 from 0b01001001/dev
- Do not overwrite paths with same name
- Merge pull request #18 from twelvelabs/path-fix
- Upgrade to v0.2.1
- Merge pull request #19 from 0b01001001/dev
- Create CONTRIBUTING.md
- Upgrade to v0.2.2
- Update to latest
- Upgrade to v0.2.3
- Change print to logging
- Upgrade to v0.2.4
- Make sure that starlette mounts are handled correctly.
- Merge pull request #26 from Prillan/fix-starlette-mount
- Update example for starlette: use Mount
- Upgrade to v0.2.5
- Refactor plugin validate
- Refactor validate interface for plugins
- Upgrade
- Merge pull request #20 from 0b01001001/dev
- Merge pull request #22 from twelvelabs/parse_request_fix
- Merge pull request #23 from 0b01001001/dev
- Merge pull request #24 from 0b01001001/dev
- Merge branch 'master' into dev
- Refactor plugin validate
- Refactor validate interface for plugins
- Upgrade
- Merge branch 'master' of github.com:0b01001001/spectree into dev
- Merge pull request #30 from 0b01001001/dev
- Upgrade openapi version to 3.0.3
- Merge pull request #34 from 0b01001001/dev
- Update readme for HOW TO
- Upgrade to v0.2.8
- Merge pull request #35 from 0b01001001/dev
- Upgrade to v0.2.9
- Merge pull request #37 from 0b01001001/dev
- Update readme: logging
- Upgrade to v0.3.0
- Merge pull request #38 from 0b01001001/dev
- Enable Response HTTP code with None instead of a string
- Merge pull request #40 from 0b01001001/dev
- Separate req data func
- Separate request validation part as a function
- Change to more reasonable names in request validation function
- Upgrade to v0.3.1
- Handle json decode error in starlette
- Upgrade to v0.3.2
- Merge pull request #41 from 0b01001001/dev
- Change trigger condition
- Upgrade to v0.3.3
- Every push should trigger ci
- Merge pull request #44 from 0b01001001/dev

### Fixed

- Fix starlette json bug(caused by json.loads(b''))
- Test falcon `self`
- Fix #21
- Fix starlette Mount, add examples and tests (#27)
- Fix headers and cookies generated in openapi file
- Fix demo bug
- Fix starlette path variable bug
- Fix test for response
- Fix test for spectree backend arg
- Fix starlette json decode error return

### Removed

- Remove requestBody field for operations that don't have them
- Remove dev trigger

## [0.2] - 2020-01-06

### Added

- Add test for response
- Add test for utils
- Add test for spec
- Add test for plugins
- Add docs
- Additional lib
- Add flask demo

### Changed

- Update issue templates
- Create LICENSE
- Change falcon response to origin format, fix falcon bypass fucntion
- Merge pull request #13 from 0b01001001/dev
- Change flask response to jsonify, fix make_response part(header and status code)
- Merge pull request #14 from 0b01001001/dev
- Change falcon json obj from media to json
- Delete unused lib
- Install starlette[full] with requests support
- Merge pull request #15 from 0b01001001/dev
- Merge pull request #16 from 0b01001001/dev

### Fixed

- Fix starlette validation error response
- Fix test

## [0.1] - 2019-12-24

### Added

- Add github actions
- Add badges, publish to pypi
- Add doc for response, utils, spectree
- Add examples
- Add config for flake8
- Add falcon plugin
- Add response, finish arch
- Add flask support
- Add flask demo
- Add another route to falcon demo
- Add utils
- Support starlette
- Add starlette demo
- Update readme: add code quality badge
- Support headers and cookies
- Update flask demo: add headers
- Update readme: add cookies
- Add py3.8, remove generate doc

### Changed

- Initial commit
- Init test, add test for config
- Init structure, add config
- Init
- Init docs
- Init plugin
- Init spec
- Refactoring Response
- Update flask interface
- Merge pull request #4 from 0b01001001/dev
- Change to render two ui pages with their name
- Update interface, fix falcon
- Merge pull request #5 from 0b01001001/dev
- Change context class to namestuple
- Merge pull request #6 from 0b01001001/dev
- Update readme: access data
- Move CONST to class init func
- Merge pull request #9 from 0b01001001/dev
- Merge pull request #10 from 0b01001001/dev
- Also check tests and examples
- Release v0.1
- Merge pull request #11 from 0b01001001/dev

### Fixed

- Fix github action folder
- Fix readme setup
- Fix http code, validationerror json
- Fix nested for duplicated variable name
- Fix base interface, fix flask register function
- Fix lambda closure bug

[unreleased]: https://github.com/0b01001001/spectree/compare/v2.0.1..HEAD
[2.0.1]: https://github.com/0b01001001/spectree/compare/v2.0.0..v2.0.1
[2.0.0]: https://github.com/0b01001001/spectree/compare/v2.0.0a1..v2.0.0
[2.0.0a1]: https://github.com/0b01001001/spectree/compare/v2.0.0a0..v2.0.0a1
[2.0.0a0]: https://github.com/0b01001001/spectree/compare/v1.5.8..v2.0.0a0
[1.5.8]: https://github.com/0b01001001/spectree/compare/v1.5.7..v1.5.8
[1.5.7]: https://github.com/0b01001001/spectree/compare/v1.5.6..v1.5.7
[1.5.6]: https://github.com/0b01001001/spectree/compare/v1.5.5..v1.5.6
[1.5.5]: https://github.com/0b01001001/spectree/compare/v1.5.4..v1.5.5
[1.5.4]: https://github.com/0b01001001/spectree/compare/v1.5.3..v1.5.4
[1.5.3]: https://github.com/0b01001001/spectree/compare/v1.5.2..v1.5.3
[1.5.2]: https://github.com/0b01001001/spectree/compare/v1.5.1..v1.5.2
[1.5.1]: https://github.com/0b01001001/spectree/compare/v1.5.0..v1.5.1
[1.5.0]: https://github.com/0b01001001/spectree/compare/v1.4.12..v1.5.0
[1.4.12]: https://github.com/0b01001001/spectree/compare/v1.4.11..v1.4.12
[1.4.11]: https://github.com/0b01001001/spectree/compare/v1.4.10..v1.4.11
[1.4.10]: https://github.com/0b01001001/spectree/compare/v1.4.9..v1.4.10
[1.4.9]: https://github.com/0b01001001/spectree/compare/v1.4.8..v1.4.9
[1.4.8]: https://github.com/0b01001001/spectree/compare/v1.4.7..v1.4.8
[1.4.7]: https://github.com/0b01001001/spectree/compare/v1.4.6..v1.4.7
[1.4.6]: https://github.com/0b01001001/spectree/compare/v1.4.5..v1.4.6
[1.4.5]: https://github.com/0b01001001/spectree/compare/v1.4.4..v1.4.5
[1.4.4]: https://github.com/0b01001001/spectree/compare/v1.4.3..v1.4.4
[1.4.3]: https://github.com/0b01001001/spectree/compare/v1.4.2..v1.4.3
[1.4.2]: https://github.com/0b01001001/spectree/compare/v1.4.1..v1.4.2
[1.4.1]: https://github.com/0b01001001/spectree/compare/v1.4.0..v1.4.1
[1.4.0]: https://github.com/0b01001001/spectree/compare/v1.3.0..v1.4.0
[1.3.0]: https://github.com/0b01001001/spectree/compare/v1.2.11..v1.3.0
[1.2.11]: https://github.com/0b01001001/spectree/compare/v1.2.10..v1.2.11
[1.2.10]: https://github.com/0b01001001/spectree/compare/v1.2.9..v1.2.10
[1.2.9]: https://github.com/0b01001001/spectree/compare/v1.2.8..v1.2.9
[1.2.8]: https://github.com/0b01001001/spectree/compare/v1.2.7..v1.2.8
[1.2.7]: https://github.com/0b01001001/spectree/compare/v1.2.6..v1.2.7
[1.2.6]: https://github.com/0b01001001/spectree/compare/v1.2.5..v1.2.6
[1.2.5]: https://github.com/0b01001001/spectree/compare/v1.2.4..v1.2.5
[1.2.4]: https://github.com/0b01001001/spectree/compare/v1.2.3..v1.2.4
[1.2.3]: https://github.com/0b01001001/spectree/compare/v1.2.2..v1.2.3
[1.2.2]: https://github.com/0b01001001/spectree/compare/v1.2.1..v1.2.2
[1.2.1]: https://github.com/0b01001001/spectree/compare/v1.2.0..v1.2.1
[1.2.0]: https://github.com/0b01001001/spectree/compare/v1.1.5..v1.2.0
[1.1.5]: https://github.com/0b01001001/spectree/compare/v1.1.4..v1.1.5
[1.1.4]: https://github.com/0b01001001/spectree/compare/v1.1.3..v1.1.4
[1.1.3]: https://github.com/0b01001001/spectree/compare/v1.1.2..v1.1.3
[1.1.2]: https://github.com/0b01001001/spectree/compare/v1.1.1..v1.1.2
[1.1.1]: https://github.com/0b01001001/spectree/compare/v1.1.0..v1.1.1
[1.1.0]: https://github.com/0b01001001/spectree/compare/v1.0.3..v1.1.0
[1.0.3]: https://github.com/0b01001001/spectree/compare/v1.0.2..v1.0.3
[1.0.2]: https://github.com/0b01001001/spectree/compare/v1.0.1..v1.0.2
[1.0.1]: https://github.com/0b01001001/spectree/compare/v1.0.0a4..v1.0.1
[1.0.0a4]: https://github.com/0b01001001/spectree/compare/v1.0.0a3..v1.0.0a4
[1.0.0a3]: https://github.com/0b01001001/spectree/compare/v1.0.0a2..v1.0.0a3
[1.0.0a2]: https://github.com/0b01001001/spectree/compare/v1.0.0a1..v1.0.0a2
[1.0.0a1]: https://github.com/0b01001001/spectree/compare/v1.0.0a0..v1.0.0a1
[1.0.0a0]: https://github.com/0b01001001/spectree/compare/v0.10.3..v1.0.0a0
[0.10.3]: https://github.com/0b01001001/spectree/compare/v0.10.2..v0.10.3
[0.10.2]: https://github.com/0b01001001/spectree/compare/v0.10.1..v0.10.2
[0.10.1]: https://github.com/0b01001001/spectree/compare/v0.10.0..v0.10.1
[0.10.0]: https://github.com/0b01001001/spectree/compare/v0.10.0a1..v0.10.0
[0.10.0a1]: https://github.com/0b01001001/spectree/compare/v0.9.2..v0.10.0a1
[0.9.2]: https://github.com/0b01001001/spectree/compare/v0.9.1..v0.9.2
[0.9.1]: https://github.com/0b01001001/spectree/compare/v0.9.0..v0.9.1
[0.9.0]: https://github.com/0b01001001/spectree/compare/v0.8.0..v0.9.0
[0.8.0]: https://github.com/0b01001001/spectree/compare/v0.7.6..v0.8.0
[0.7.6]: https://github.com/0b01001001/spectree/compare/v0.7.5..v0.7.6
[0.7.5]: https://github.com/0b01001001/spectree/compare/v0.7.4..v0.7.5
[0.7.4]: https://github.com/0b01001001/spectree/compare/v0.7.3..v0.7.4
[0.7.3]: https://github.com/0b01001001/spectree/compare/v0.7.2..v0.7.3
[0.7.2]: https://github.com/0b01001001/spectree/compare/v0.7.1..v0.7.2
[0.7.1]: https://github.com/0b01001001/spectree/compare/v0.7.0..v0.7.1
[0.7.0]: https://github.com/0b01001001/spectree/compare/v0.6.8..v0.7.0
[0.6.8]: https://github.com/0b01001001/spectree/compare/v0.6.7..v0.6.8
[0.6.7]: https://github.com/0b01001001/spectree/compare/v0.6.6..v0.6.7
[0.6.6]: https://github.com/0b01001001/spectree/compare/v0.6.5..v0.6.6
[0.6.5]: https://github.com/0b01001001/spectree/compare/v0.6.4..v0.6.5
[0.6.4]: https://github.com/0b01001001/spectree/compare/v0.6.3..v0.6.4
[0.6.3]: https://github.com/0b01001001/spectree/compare/v0.6.2..v0.6.3
[0.6.2]: https://github.com/0b01001001/spectree/compare/v0.6.1..v0.6.2
[0.6.1]: https://github.com/0b01001001/spectree/compare/v0.6.0..v0.6.1
[0.6.0]: https://github.com/0b01001001/spectree/compare/v0.5.4..v0.6.0
[0.5.4]: https://github.com/0b01001001/spectree/compare/v0.5.3..v0.5.4
[0.5.3]: https://github.com/0b01001001/spectree/compare/v0.5.2..v0.5.3
[0.5.2]: https://github.com/0b01001001/spectree/compare/v0.5.1..v0.5.2
[0.5.1]: https://github.com/0b01001001/spectree/compare/v0.5.0..v0.5.1
[0.5.0]: https://github.com/0b01001001/spectree/compare/v0.4.3..v0.5.0
[0.4.3]: https://github.com/0b01001001/spectree/compare/v0.4.2..v0.4.3
[0.4.2]: https://github.com/0b01001001/spectree/compare/v0.4.1..v0.4.2
[0.4.1]: https://github.com/0b01001001/spectree/compare/v0.4.0..v0.4.1
[0.4.0]: https://github.com/0b01001001/spectree/compare/v0.3.16..v0.4.0
[0.3.16]: https://github.com/0b01001001/spectree/compare/v0.3.15..v0.3.16
[0.3.15]: https://github.com/0b01001001/spectree/compare/v0.3.14..v0.3.15
[0.3.14]: https://github.com/0b01001001/spectree/compare/v0.3.13..v0.3.14
[0.3.13]: https://github.com/0b01001001/spectree/compare/v0.3.12..v0.3.13
[0.3.12]: https://github.com/0b01001001/spectree/compare/v0.3.11..v0.3.12
[0.3.11]: https://github.com/0b01001001/spectree/compare/v0.3.10..v0.3.11
[0.3.10]: https://github.com/0b01001001/spectree/compare/v0.3.9..v0.3.10
[0.3.9]: https://github.com/0b01001001/spectree/compare/v0.3.7..v0.3.9
[0.3.7]: https://github.com/0b01001001/spectree/compare/v0.3.3..v0.3.7
[0.3.3]: https://github.com/0b01001001/spectree/compare/v0.2..v0.3.3
[0.2]: https://github.com/0b01001001/spectree/compare/v0.1..v0.2
[0.1]: https://github.com/0b01001001/spectree/tree/v0.1

<!-- generated by git-cliff -->
