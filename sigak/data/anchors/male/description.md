# SIGAK 남성 8앵커 AI 레퍼런스 생성 가이드

> 3축: Shape(Soft↔Sharp) × Volume(Subtle↔Bold) × Age(Fresh↔Mature)
> 여성 8앵커와 동일 좌표계, 동일 꼭짓점, 표현만 남성화

---

## 여성 → 남성 전환 원칙

| 항목 | 여성 | 남성 |
|------|------|------|
| 메이크업 | 유형별 톤 반영 | 없음 (clean skin) |
| 헤어 | 웨이브/스트레이트/앞머리 | 짧은 컷 위주, 유형별 분기 |
| 표정 | 미소/무표정/절제된 미소 | 동일 분기 유지 |
| 나이 | Fresh=early 20s, Mature=late 20s~30s | 동일 |
| 피부 | warm/cool tone + makeup | 피부톤만, makeup 제거 |
| 체모 | 없음 | clean shaven 기본 (8M만 stubble 허용) |
| 골격 표현 | "부드러운 턱선" | "부드러운 턱선" 유지 (남성도 soft 존재) |

---

## 공통 프롬프트 꼬리

```
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## 8앵커 전체 맵

```
              Fresh
                │
    1M 따뜻한  │  3M 차가운
       소년    │     동안
    2M 귀여운  │  4M 또렷한
       존재감  │     에너지
  Soft ────────┼──────── Sharp
    5M 편안한  │  7M 절제된
       형      │     시크
    6M 부드러운│  8M 날카로운
       카리스마│     카리스마
                │
             Mature

점 크기 = Volume (Subtle=작은점, Bold=큰점)
1M,3M,5M,7M = Subtle (작은 점)
2M,4M,6M,8M = Bold (큰 점)
```

---

## Type 1M: 따뜻한 소년

**Shape -0.8 / Volume -0.7 / Age -0.8**
**Soft · Subtle · Fresh**

구조적 특징:
- 둥근 얼굴형, 부드러운 턱선
- 작고 온화한 눈, 약간 처진 눈꼬리
- 얇은 입술, 낮고 둥근 코
- 넓은 이마, 볼살, 짧은 인중
- 전체적으로 작고 부드럽고 어린

```
Korean man, early 20s, round face shape with soft rounded jawline,
small gentle eyes with slightly downturned outer corners,
thin natural lips, small nose with rounded tip,
wide forehead, soft full cheeks, short philtrum,
small delicate features overall,
warm-toned clear skin, clean shaven,
gentle innocent expression with slight smile,
short dark brown hair with soft texture and natural side part,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## Type 2M: 귀여운 존재감

**Shape -0.8 / Volume +0.8 / Age -0.8**
**Soft · Bold · Fresh**

구조적 특징:
- 둥근 얼굴형, 부드러운 턱선
- 크고 또렷한 눈, 온화하지만 강렬한 이목구비
- 도톰한 입술, 높은 코
- 어린 비율에 큰 이목구비 — 눈에 띄는 귀여움

```
Korean man, early 20s, round face with soft jawline,
very large expressive eyes with warm bright gaze and natural double eyelids,
full lips with defined shape, prominent nose with soft bridge,
full cheeks, short philtrum,
big striking features on round youthful face,
warm-toned glowing skin, clean shaven,
bright cheerful expression with wide smile,
dark brown hair with fluffy texture and slight comma bangs,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## Type 3M: 차가운 동안

**Shape +0.8 / Volume -0.7 / Age -0.8**
**Sharp · Subtle · Fresh**

구조적 특징:
- 역삼각형 얼굴, 뾰족한 턱
- 날카로운 눈매, 올라간 눈꼬리, 작은 눈
- 높은 코, 얇은 입술
- 작은 이목구비에 어린 비율 — 차갑고 시크한 동안

```
Korean man, early 20s, small inverted triangle face with sharp chin,
narrow eyes with sharp upturned corners and cool distant gaze,
high straight nose bridge with defined tip, thin small lips,
small refined features on angular youthful face,
fair cool-toned skin, clean shaven,
calm cold expression with closed lips,
black straight hair with clean middle part,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## Type 4M: 또렷한 에너지

**Shape +0.8 / Volume +0.8 / Age -0.8**
**Sharp · Bold · Fresh**

구조적 특징:
- 각진 얼굴, 날카로운 턱선
- 크고 날카로운 눈, 뚜렷한 쌍꺼풀
- 높은 코, 두꺼운 입술
- 큰 이목구비 + 어린 비율 — 화려하고 에너지 넘치는 동안

```
Korean man, early 20s, angular face with defined sharp jawline,
large intense eyes with clear double eyelids and bright sharp gaze,
high prominent nose bridge, full defined lips,
bold expressive features with strong presence,
bright warm-toned skin, clean shaven,
energetic confident expression with slight smirk,
dark brown hair with textured two-block cut and volume on top,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## Type 5M: 편안한 형

**Shape -0.8 / Volume -0.7 / Age +0.8**
**Soft · Subtle · Mature**

구조적 특징:
- 타원형 얼굴, 부드러운 턱선에 길이감
- 중간 크기 눈, 잔잔한 눈매
- 자연스러운 코, 얇은 입술
- 작은 이목구비 + 성숙한 비율 — 편안하고 신뢰감 있는

```
Korean man, late 20s to early 30s, oval face with soft elongated jawline,
medium-sized eyes with gentle calm steady gaze, natural brow shape,
proportional nose, thin natural lips,
understated refined features on mature face,
warm-toned skin with natural healthy tone, clean shaven,
serene reliable expression with subtle smile,
dark brown hair neatly combed to the side, short and clean,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## Type 6M: 부드러운 카리스마

**Shape -0.8 / Volume +0.8 / Age +0.8**
**Soft · Bold · Mature**

구조적 특징:
- 타원형~둥근 얼굴, 부드러운 턱선
- 크고 깊은 눈, 온화하지만 깊이 있는 눈매
- 도톰한 입술, 높은 코
- 큰 이목구비 + 성숙한 비율 — 온화하면서 압도적

```
Korean man, late 20s, oval to round face with soft jawline,
large deep-set eyes with warm intense gaze and thick natural brows,
full prominent lips, nose with strong but soft bridge,
bold expressive features with commanding warm presence,
warm-toned skin with rich healthy glow, clean shaven,
confident warm expression with steady gaze,
dark brown hair with natural wave and slight length on top,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## Type 7M: 절제된 시크

**Shape +0.8 / Volume -0.7 / Age +0.8**
**Sharp · Subtle · Mature**

구조적 특징:
- 긴 얼굴형, 각진 턱선, 높은 광대
- 가늘고 올라간 눈, 날카로운 눈매
- 높은 코, 얇은 입술
- 작은 이목구비 + 성숙한 비율 — 차갑고 절제된 시크

```
Korean man, late 20s to early 30s, long face with angular defined jawline,
narrow elongated eyes with sharp upturned gaze,
high prominent cheekbones, straight tall nose bridge,
thin lips with defined edges, long philtrum,
small refined features with restrained cold elegance,
fair cool-toned skin, clean shaven,
composed reserved expression with closed lips,
black hair slicked back cleanly with no bangs,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## Type 8M: 날카로운 카리스마

**Shape +0.8 / Volume +0.8 / Age +0.8**
**Sharp · Bold · Mature**

구조적 특징:
- 긴 각진 얼굴, 강한 턱선
- 크고 날카로운 눈, 강렬한 눈매, 짙은 눈썹
- 높은 코, 두꺼운 입술
- 큰 이목구비 + 성숙한 비율 — 압도적 카리스마

```
Korean man, late 20s, long angular face with strong defined jawline,
large dramatic eyes with sharp intense upturned gaze, thick bold brows,
high sculpted cheekbones, tall prominent nose bridge,
full bold lips, strong brow ridge,
large commanding features with overwhelming masculine presence,
fair cool-toned skin, light stubble allowed,
powerful confident expression with direct gaze,
black hair styled back with volume,
white seamless background, portrait photography, soft flat lighting.
No accessories. No glasses.
```

---

## 여성-남성 앵커 대응표

| # | 여성 이름 | 남성 이름 | 좌표 | 사분면 |
|---|----------|----------|------|--------|
| 1 | 따뜻한 첫사랑 | 따뜻한 소년 | Soft/Subtle/Fresh | Soft Fresh |
| 2 | 사랑스러운 인형 | 귀여운 존재감 | Soft/Bold/Fresh | Soft Fresh |
| 3 | 차갑지만 동안 | 차가운 동안 | Sharp/Subtle/Fresh | Sharp Fresh |
| 4 | 또렷한 에너지 | 또렷한 에너지 | Sharp/Bold/Fresh | Sharp Fresh |
| 5 | 편안한 우아함 | 편안한 형 | Soft/Subtle/Mature | Soft Mature |
| 6 | 부드러운 카리스마 | 부드러운 카리스마 | Soft/Bold/Mature | Soft Mature |
| 7 | 절제된 시크 | 절제된 시크 | Sharp/Subtle/Mature | Sharp Mature |
| 8 | 날카로운 카리스마 | 날카로운 카리스마 | Sharp/Bold/Mature | Sharp Mature |

이름이 겹치는 유형(4,6,7,8)은 의도적 — 성별 무관하게 같은 인상이므로.
이름이 다른 유형(1,2,3,5)은 남성 맥락에서 더 자연스러운 표현으로 조정.

---

## 남성 전용 헤어 가이드

| 유형 | 헤어 | 이유 |
|------|------|------|
| 1M 따뜻한 소년 | 짧은 사이드파트, 부드러운 텍스처 | 순한 인상 강화 |
| 2M 귀여운 존재감 | 쉼표머리, 약간의 볼륨 | 귀엽고 트렌디 |
| 3M 차가운 동안 | 가르마, 직모 | 서늘하고 깔끔 |
| 4M 또렷한 에너지 | 투블럭 + 윗머리 볼륨 | 에너지, 역동적 |
| 5M 편안한 형 | 짧고 단정한 옆가르마 | 신뢰감, 편안함 |
| 6M 부드러운 카리스마 | 약간 긴 윗머리 + 웨이브 | 여유, 카리스마 |
| 7M 절제된 시크 | 올백, 뱅 없음 | 절제, 시크 |
| 8M 날카로운 카리스마 | 볼륨 올백 | 강렬, 압도적 |

---

## 생성 규칙 (남성 공통)

1. **배경:** white seamless
2. **조명:** soft flat lighting
3. **표정:** Fresh=미소/밝은, Mature=절제된/차분한
4. **메이크업:** 없음. 피부톤만 반영
5. **체모:** clean shaven 기본. 8M(날카로운 카리스마)만 light stubble 허용
6. **악세사리:** 전부 없음
7. **나이:** Fresh=early 20s, Mature=late 20s~early 30s
8. **인종:** "Korean man" 명시
9. **의상:** 보이지 않게 (portrait crop) 또는 무채색 크루넥

## 품질 체크리스트

- [ ] 특정 셀럽/아이돌로 식별 가능한가? → 폐기
- [ ] 여성 앵커와 나란히 놓았을 때 같은 유형 느낌인가?
- [ ] 8장 나란히 놓았을 때 유형 간 차이가 직관적인가?
- [ ] AI 생성 티가 심한가? (언캐니밸리 체크)
- [ ] 시리즈 통일감 있는가?

---

*Generated: 2026-04-09*
*여성 8앵커 가이드와 동일 좌표계. Phase 12-1 (남성 파이프라인 분기) 시 사용.*