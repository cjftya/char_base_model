# char_base_model

Blender에서 Phase 0의 정투영 레퍼런스 환경 설정과 Phase 1의 실측 기반 신체·머리 베이스 메시 생성을 수행하는 에이전트 스킬이에요.

## Blender MCP로 실행하기

1. Blender를 실행하고 CLI를 기존 Blender MCP에 연결해 주세요. 스킬이 현재 장면과 사용 가능한 기능을 확인해요.
2. 저장소의 폴더 구조를 유지한 상태에서 CLI의 프로젝트 스킬 등록 방식으로 [skills/char-base-model](skills/char-base-model)을 등록하거나, CLI에 해당 폴더의 `SKILL.md`를 직접 읽도록 요청해 주세요.
3. 에이전트에 이미지가 있는 폴더를 알려주거나 `front`, `back`, `left`, `right`라는 이름의 파일 4개를 첨부해 주세요. 확장자는 각각 `.png`, `.jpg`, `.jpeg`를 사용할 수 있어요. 요청 예시: “이 4장의 이미지로 char-base-model을 실행해 줘. 작업 결과는 /home/me/models 아래에 저장해 줘.”
4. 스킬은 지정한 저장 위치 아래에 `char_base_YYYYMMDD_HHMMSS` 폴더를 만들고 입력 이미지를 복사해요. 위치를 지정하지 않으면 Blender가 실행 중인 Windows 또는 Linux의 다운로드 폴더를 사용해요. 각 실행 폴더에는 레퍼런스, 설정, Blender 작업 사본, 매니페스트가 저장돼요. 스킬과 하네스는 저장소에 그대로 유지돼요.
5. 에이전트가 이미지를 확인하고 실행별 기준점을 보정한 뒤, MCP를 통해 열려 있는 Blender 장면을 준비해요. 이미지의 짧은 변이 512px 미만이면 더 큰 원본이 필요해요. 이미지마다 해상도가 다르면 개별 기준점 보정 방법을 안내해요. 자세한 내용은 [입력 규칙](skills/char-base-model/references/input-spec.md)을 참고해 주세요.
6. 네 방향을 모두 확인하고 저장된 사본을 다시 열어 검토해 주세요. [검토 체크리스트](skills/char-base-model/references/workflow.md)를 통과하기 전까지 결과는 `UNVERIFIED` 상태로 유지돼요.

Blender에서 이미지에 접근할 수 없으면 Blender가 실행 중인 컴퓨터에 이미지를 저장하도록 안내해요. 필요한 방향이 빠졌거나 이미지가 적합하지 않거나 MCP 기능을 사용할 수 없으면 해당 입력 또는 연결에 대한 해결 방법을 안내해요.

## 보조 스크립트와 선택적 Blender 백그라운드 실행

일반적으로 에이전트는 MCP를 통해 Blender가 실행 중인 컴퓨터에서 다음 스크립트를 호출해요. 입력 준비만 별도로 실행할 때는 Python 3.11 이상이 필요하며, 표준 라이브러리만 사용해요.

```bash
python scripts/prepare_session.py /path/to/input-images
python scripts/prepare_session.py /path/to/input-images --destination /path/to/work-parent
python scripts/prepare_session.py /path/front.jpg /path/back.png /path/left.jpeg /path/right.jpg
```

Windows에서는 Windows 형식의 경로를 사용하고, 필요하면 따옴표로 감싸 주세요. 보조 스크립트는 Windows의 위치가 변경된 다운로드 폴더와 Linux의 XDG 다운로드 폴더를 인식해요. 저장 위치를 명시하면 해당 경로를 우선 사용하며, 지정한 폴더는 미리 존재해야 해요. 세션의 초기 기준점은 실제 이미지를 확인한 뒤에만 `anchors_reviewed`를 true로 설정해야 해요.

필요하면 별도의 Blender 4.x 백그라운드 프로세스에서도 준비된 세션 설정을 사용할 수 있어요.

```bash
blender --background --factory-startup --python-exit-code 2 \
  --python scripts/setup_references.py -- \
  --config /path/char_base_YYYYMMDD_HHMMSS/config/reference_setup.json \
  --output /path/char_base_YYYYMMDD_HHMMSS/reference_stage.blend
```

저장을 재시도할 때는 새로운 출력 파일명을 사용해 주세요. 백그라운드 실행에서 `--overwrite`를 지정하면 기존 출력과 매니페스트를 명시적으로 덮어써요. 현재 열려 있는 원본 파일은 보호돼요.

## 개발 및 테스트

```bash
python -m unittest discover -s tests -v
```

테스트는 Blender API를 모의 구현해 입력 파일 헤더와 기준점 보정, 세션 입력 준비, 저장 경로 결정, 장면 및 출력 안전성을 검증해요. 실제 뷰포트 표시, Blender의 이미지 디코딩, UI 잠금, 저장 후 다시 열었을 때의 상태 유지는 Blender와 실제 이미지로 확인해야 해요. 이후 단계의 역할별 계약은 [워크플로 문서](docs/workflow.md)를 참고해 주세요.

## Phase 1: 레퍼런스 기반 베이스 메시

Phase 0의 화면 검토와 저장 파일 재열기 검증을 통과한 뒤, 에이전트에 Phase 1을 이어서 진행하도록 요청해 주세요. [모델링 워크플로](skills/char-base-model/references/phase1-modeling.md), [검토 규칙](skills/char-base-model/references/phase1-review.md), [데이터 계약](contracts/phase1-format.md)을 참고해 주세요.

기존 Blender MCP를 통해 Blender가 실행 중인 컴퓨터에서 다음 모듈을 호출해요.

- `phase1_analysis.py`: 보정된 이미지 좌표를 월드 좌표로 변환해 치수를 측정하고, 방향별 오차를 계산해요.
- `phase1_contract.py`: 원본 식별값의 불변성, 실측 기반 계약, 출력 디렉터리의 정확한 재지정, 순차 검증 단계, 재작업 횟수 제한을 관리해요.
- `phase1_junction.py`: 연결부의 정점 대응·뒤집힌 방향·접힌 면·브리지 엣지 교차를 검사해요.
- `phase1_replan.py`: 실패 세션의 계약과 체크포인트를 보존하면서 새 실측 초안과 세션을 만들어요.
- `phase1_geometry.py`: 링과 분기 구조로 연결된 신체, 두개골과 통합된 눈·입·귀 형상을 생성해요. 닫힌 표면을 검증하고, 선택적으로 마스크 기반 지표를 계산해요.
- `phase1_blender.py`: 원본을 보호하는 작업 사본, Body/Head 생성기, 기록이 남는 국소 정점 수정, BMesh 법선 보정, 렌더 6장, 보정된 오버레이 4장, 읽기 전용 메시 통계, 검증 근거 연결, 검증 단계 통과 후 최종 저장을 담당해요.

에이전트는 현재 이미지를 측정해 단면 프로파일과 랜드마크를 제공해요. 이미지를 자동으로 해부학적 구조로 변환하는 신경망 모델을 사용하거나, 일반적인 신체 비율로 대체하지는 않아요. 형상을 먼저 검토한 뒤 엣지 루프를 다듬어요. 머리와 신체는 각각 별도의 닫힌 메시로 유지하며, 두 메시가 공유하는 목 연결 규격을 시각적으로 검토해요. 이 파이프라인의 범위는 베이스 모델링이며, 리깅에 바로 사용할 수 있는 리토폴로지를 자동으로 완성하는 단계는 아니에요.

단위 테스트는 합성 지오메트리, 계약, 입력 보존, 검증 단계를 확인해요. 실제 캐릭터와의 닮은 정도까지 입증하지는 못해요. 연결된 Blender 환경에서 실제 세션을 실행하기 전까지 Blender/MCP 실행과 캐릭터 유사도는 미검증 상태예요. 현재 검증 근거와 한계는 [구현 검증 문서](docs/phase1-validation.md)를 참고해 주세요. Phase 1에는 새로운 MCP 서버, 리깅, 머리카락, 의상, 재질, 애니메이션이 추가되지 않아요.

폴리곤 생성과 결과 승인에는 공통 [폴리곤 정책](config/polygon_policy.json)을 적용해요. Phase 1 계약을 작성하기 전에 [밀도 계획·개수 집계·실패 처리](docs/phase1-polygon-budget.md)를 읽어 주세요. 폴리곤 예산 검사 과정에서 실측 기반 형상에 Decimate, 세분화, 리메시를 자동 적용하지 않아요.

미드폴리곤 개선에서는 어깨·골반에 실측 전이 링을 지정할 수 있고, 종아리 폭과
양쪽 측면 깊이를 방향별로 비교해요. 기본 합계 상한은 30,000 triangles,
경고는 24,000부터예요. 16,000–24,000 참고 구간을 채우려고 링을 추가하지는 않아요.
연결 방식이 잘못된 경우에는 정점 위치 수정만 반복하지 않고 새 세션에서 다시 계획해요.
[변경 전 검토와 재테스트 절차](docs/phase1-midpoly-review.md)를 참고해 주세요.
