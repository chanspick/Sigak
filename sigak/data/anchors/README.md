# SIGAK 앵커 이미��� 디렉토리

## 개���

이 디렉토리에는 SIGAK 미적 좌표계의 기준점이 되는 셀럽 앵커 이미지를 배치합니다.
CLIP 임베딩을 통해 미적 공간의 축 방향을 데이터 기반으로 발견하는 데 사용됩니다.

**성��로 분리된 좌표계**를 사용하므로, 반드시 `female/` 또는 `male/` 하위 디렉토리에 배치합��다.

## 디렉��리 구조

```
sigak/data/anchors/
    female/
        suzy/
            suzy_001.jpg
            suzy_002.jpg
            suzy_003.jpg
        jennie/
            jennie_001.jpg
            jennie_002.jpg
            jennie_003.jpg
        ...
    male/
        won_bin/
            won_bin_001.jpg
            won_bin_002.jpg
            won_bin_003.jpg
        cha_eun_woo/
            cha_eun_woo_001.jpg
            cha_eun_woo_002.jpg
            cha_eun_woo_003.jpg
        ...
```

- 반드시 `female/` 또는 `male/` 디렉토리 안에 셀럽 폴더를 생성합니다
- 각 셀럽마�� **영문 ���름**으로 하위 폴더를 생성합니다
- 폴���명이 곧 임베딩 라벨로 사용됩니다

## 이미지 요구사항

### 반드시 지켜야 할 사항

1. **일상 사진만 사용**: 공항 패션, 브이로그 캡처, 일상 외출 사진 등
2. **화보/에디토리얼 사진 제외**: 잡지 촬영, 광고, 무대 사진 사용 금지
3. **최소 3장**, 권장 **5장 이상** (평균 임베딩의 안정성을 위해)
4. **정면 또는 약간 측면 얼굴**이 보이는 사진
5. **얼굴이 선명하게** 나온 사진 (블러 또는 저해상도 제외)

### 파일 이름 규칙

```
{셀럽_영문이름}_{번호}.jpg
```

- 예시: `suzy_001.jpg`, `suzy_002.jpg`, `won_bin_001.jpg`
- 지원 확���자: `.jpg`, `.jpeg`, `.png`

### 피해야 할 사진 유형

- 과도한 보정 또는 필터가 적용된 사진
- 선글라스, 마스크 등으로 얼굴이 가려진 사진
- 무대 메이크업, 특수 분장 사진
- 조명이 극단적인 사진 (역광, 강한 색조명)
- 흑백 사진

## 사용법

이미지를 배치한 후 임베딩 스크립트를 실행합니다:

```bash
# 성별별 임베딩 생성 (기본: female + male 모두)
python -m sigak.scripts.embed_anchors

# 특정 성별만 실행
python -m sigak.scripts.embed_anchors --gender female
python -m sigak.scripts.embed_anchors --gender male

# GPU 없이 테스트 (mock 임베딩)
python -m sigak.scripts.embed_anchors --use-mock
```

## 주의사항

- 이미지 파일은 **git에 커밋하지 않습니다** (용량 + 저작권)
- 이 디렉토리의 이미지는 로컬에서만 관리합니다
- 임베딩 결과(`.npy`, `.npz`)는 `sigak/data/embeddings/{female,male}/`에 저장됩니다
