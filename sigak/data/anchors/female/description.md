# SIGAK 유형별 AI 레퍼런스 얼굴 생성 가이드

## 원칙
- 셀럽 사진 레퍼런스 절대 사용 금지 (법적 리스크)
- 구조적 특징 키워드만으로 프롬프트 구성
- 3축 좌표의 극점 조합 = 유형 = 프롬프트

---

## 3축 정의

| 축 | 0 (음극) | 1 (양극) | CV 근거 |
|---|---|---|---|
| 인상 | 소프트 | 샤프 | 턱각도, 광대, 눈꼬리 각도 |
| 톤 | 웜·내추럴 | 쿨·글램 | 피부색 경향, 메이크업 밀도 |
| 무드 | 프레시·큐트 | 성숙·시크 | 얼굴 비율, 전체 인상 |

---

## 유형 8개 (3축 극점 조합)

### Type 1: 소프트 + 웜 + 프레시
**좌표: (0.2, 0.2, 0.2)**
**키워드: 따뜻한 첫사랑 인상**

구조적 특징:
- 둥근 얼굴형, 부드러운 턱선
- 큰 둥근 눈, 눈꼬리 살짝 처짐
- 도톰한 입술, 낮은 코
- 넓은 이마, 볼살 있음
- 짧은 인중

```
Korean woman, early 20s, round face shape with soft rounded jawline,
large round eyes with slightly downturned outer corners, full soft lips,
small nose with rounded tip, wide forehead, full cheeks, short philtrum,
warm-toned clear skin, no makeup or very minimal natural makeup,
gentle innocent expression with slight smile,
long dark brown hair with soft waves,
white seamless background, portrait photography, soft flat lighting.
No accessories. No heavy makeup.
```

---

### Type 2: 소프트 + 쿨 + 프레시
**좌표: (0.2, 0.8, 0.2)**
**키워드: 차갑지만 동안인 인상**

구조적 특징:
- 작은 달걀형 얼굴
- 큰 눈이지만 눈매가 서늘함
- 얇은 입술, 오똑한 코
- 피부가 밝고 하얗고 차가운 톤

```
Korean woman, early 20s, small oval face with slim jawline,
large eyes with cool sharp gaze but youthful proportion,
thin defined lips, straight nose bridge with refined tip,
fair cool-toned porcelain skin, light natural makeup with cool pink tones,
calm neutral expression,
straight black hair with middle part,
white seamless background, portrait photography, soft flat lighting.
No accessories.
```

---

### Type 3: 샤프 + 웜 + 프레시
**좌표: (0.8, 0.2, 0.2)**
**키워드: 또렷한데 발랄한 인상**

구조적 특징:
- 하트형 얼굴, 뾰족한 턱
- 또렷한 이목구비, 쌍꺼풀
- 높은 코, 두꺼운 입술
- 전체적으로 또렷하지만 따뜻한 느낌

```
Korean woman, early 20s, heart-shaped face with pointed chin,
defined double-lidded eyes with clear crease, expressive brows,
prominent nose bridge, full lips with defined cupid's bow,
warm golden-toned skin, natural warm-toned makeup,
bright energetic expression with wide smile,
dark brown hair with layered bangs,
white seamless background, portrait photography, soft flat lighting.
No accessories.
```

---

### Type 4: 샤프 + 쿨 + 성숙
**좌표: (0.8, 0.8, 0.8)**
**키워드: 날카롭고 시크한 인상**

구조적 특징:
- 긴 얼굴형, 각진 턱선
- 길고 올라간 눈, 날카로운 눈매
- 높은 광대, 오똑한 코
- 얇은 입술, 긴 인중

```
Korean woman, late 20s, long face with angular defined jawline,
elongated eyes with upturned outer corners and sharp gaze,
high prominent cheekbones, straight tall nose bridge,
thin lips with defined edges, long philtrum,
fair cool-toned skin, structured makeup with subtle contour,
composed serious expression with closed lips,
straight black hair pulled back or slicked,
white seamless background, portrait photography, soft flat lighting.
No accessories.
```

---

### Type 5: 소프트 + 웜 + 성숙
**좌표: (0.2, 0.2, 0.8)**
**키워드: 부드러우면서 성숙한 인상**

구조적 특징:
- 타원형 얼굴, 부드러운 턱선이지만 길이감 있음
- 중간 크기 눈, 잔잔한 눈매
- 도톰한 입술, 자연스러운 코
- 전체적으로 편안하고 우아한 느낌

```
Korean woman, late 20s to early 30s, oval face with soft but elongated jawline,
medium-sized eyes with gentle calm gaze, natural brow arch,
proportional nose, full soft lips,
warm-toned skin with healthy glow, minimal natural makeup,
serene elegant expression with subtle smile,
dark brown shoulder-length hair with gentle S-wave,
white seamless background, portrait photography, soft flat lighting.
No accessories.
```

---

### Type 6: 샤프 + 웜 + 성숙
**좌표: (0.8, 0.2, 0.8)**
**키워드: 강인하면서 따뜻한 인상**

구조적 특징:
- 사각형에 가까운 얼굴형, 넓은 턱
- 또렷한 눈매, 짙은 눈썹
- 넓은 코, 두꺼운 입술
- 전체적으로 건강하고 강한 느낌

```
Korean woman, late 20s, square-ish face with wide strong jawline,
defined eyes with thick natural brows, intense warm gaze,
wide nose bridge, full thick lips,
warm tanned skin with natural healthy tone, earthy warm makeup,
confident direct expression,
dark wavy hair with volume,
white seamless background, portrait photography, soft flat lighting.
No accessories.
```

---

### Type 7: 소프트 + 쿨 + 성숙
**좌표: (0.2, 0.8, 0.8)**
**키워드: 차가운 우아함**

구조적 특징:
- 달걀형 얼굴, 갸름한 턱
- 가늘고 긴 눈, 서늘한 눈매
- 날렵한 코, 얇은 입술
- 피부 밝고 차가운 톤, 전체적으로 절제된 느낌

```
Korean woman, early 30s, slim oval face with narrow refined jawline,
narrow elongated eyes with cool distant gaze,
sleek straight nose, thin elegant lips,
very fair cool-toned skin, minimal cool-toned makeup,
reserved graceful expression,
straight black long hair with clean lines,
white seamless background, portrait photography, soft flat lighting.
No accessories.
```

---

### Type 8: 샤프 + 쿨 + 프레시
**좌표: (0.8, 0.8, 0.2)**
**키워드: 날카로운데 어린 인상**

구조적 특징:
- 작은 역삼각형 얼굴, 뾰족한 턱
- 큰 눈이지만 눈매가 날카로움
- 높은 코, 작은 입
- 피부 밝고 차가운 톤, 동안이지만 시크

```
Korean woman, early 20s, small inverted triangle face with sharp chin,
large eyes with sharp inner corners and alert gaze,
high nose bridge with defined tip, small thin lips,
fair cool-toned bright skin, light cool-toned makeup,
youthful but intense expression,
black hair with short or bob cut, blunt bangs,
white seamless background, portrait photography, soft flat lighting.
No accessories.
```

---

## 남성 버전 (동일 구조, 키워드만 변경)

모든 프롬프트에서:
- "Korean woman" → "Korean man"
- "makeup" 관련 키워드 제거
- "hair" 길이/스타일을 남성형으로 변경
- 나이대 조정 (early~late 20s 기본)

예시 (Type 4 남성):
```
Korean man, late 20s, long face with angular defined jawline,
elongated eyes with sharp upturned gaze,
high prominent cheekbones, straight tall nose bridge,
thin lips, defined brow ridge,
fair cool-toned skin, clean shaven,
composed serious expression,
short black hair styled back,
white seamless background, portrait photography, soft flat lighting.
```

---

## 생성 규칙

1. **배경:** 전부 white seamless — 리포트 삽입 시 통일감
2. **조명:** soft flat lighting — 그림자 최소화, 구조 강조
3. **표정:** 유형별 차별화 (프레시=미소, 시크=무표정, 성숙=절제된 미소)
4. **헤어:** 유형별 차별화 (소프트=웨이브, 샤프=스트레이트, 프레시=앞머리)
5. **메이크업:** 톤 축 반영 (웜=내추럴/골드, 쿨=핑크/무채색)
6. **악세사리:** 전부 없음 — 얼굴 구조에 집중
7. **나이:** 프레시=early 20s, 성숙=late 20s~early 30s
8. **인종:** "Korean" 명시 — 미명시 시 서양인으로 빠짐

## 품질 체크리스트

- [ ] 특정 셀럽으로 식별 가능한가? → 가능하면 폐기
- [ ] 같은 유형 내에서 2-3명 뽑았을 때 "같은 타입"으로 읽히는가?
- [ ] 다른 유형과 나란히 놓았을 때 차이가 직관적으로 보이는가?
- [ ] AI 생성 티가 심하게 나는가? (언캐니밸리 체크)
- [ ] 배경/조명/구도가 시리즈로 통일되는가?

## 리포트 내 사용 위치

| 리포트 섹션 | 이미지 용도 |
|---|---|
| face_structure | 유저의 유형 대표 이미지 1장 |
| coordinate_map | 현재 유형 + 추구미 유형 2장 나란히 |
| celeb_reference | 유사 유형 대표 이미지 (셀럽 사진 대체) |
| action_plan | 방향 제안 시 "이 방향의 인상" 이미지 |

## 사용 툴
- Midjourney: --style raw --v 6.1 권장
- DeeVid AI: 아까 지수 타입에서 잘 나옴 (단 워터마크 제거 필요)
- Generated Photos: 파라미터 제어 필요 시
