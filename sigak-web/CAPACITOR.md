# Capacitor Native Wrap — SIGAK

**모드**: Server mode (WebView URL wrapper, `https://sigak.asia`).
**전환**: App Store 심사 시 정적 번들 모드로. 아래 "전환" 섹션 참조.

---

## 사전 요구사항

| 플랫폼 | 필요 |
|---|---|
| 공통 | Node 22 LTS, pnpm 10 |
| iOS | macOS + Xcode 15+, iOS Simulator (M 시리즈 Mac 권장) |
| Android | Android Studio Hedgehog+, JDK 21, Android SDK 34 |

---

## 로컬 초기 세팅

### 1. 의존성 설치

```bash
cd sigak-web
pnpm install
```

`@capacitor/core`, `@capacitor/ios`, `@capacitor/android`, `@capacitor/cli` 가 설치됩니다.

### 2. 네이티브 플랫폼 추가 (1회)

```bash
npx cap add ios
npx cap add android
```

→ `sigak-web/ios/` 와 `sigak-web/android/` 디렉토리 생성.
→ `.gitignore`는 팀 컨벤션에 따라 결정:
- 커밋 안 함: 각 개발자가 매번 `cap add` (빠름, merge conflict 없음)
- 커밋 함: iOS Info.plist / Android Manifest 수정사항 팀 공유 (네이티브 기능 추가 시 권장)

MVP 기간 권장: **커밋 안 함** — 아래 `.gitignore` 예시 참조.

### 3. 동기화

```bash
npx cap sync
```

`capacitor.config.ts` 내용을 네이티브 프로젝트에 반영. 서버 모드라면 웹 빌드 없이 config만 동기화.

### 4. 네이티브 IDE 열기

```bash
pnpm cap:ios       # Xcode 오픈
pnpm cap:android   # Android Studio 오픈
```

각 IDE에서 Run 버튼으로 시뮬레이터/에뮬레이터 실행.

---

## 동작 원리 (Server mode)

앱 실행 → Capacitor WebView가 `https://sigak.asia` 로드 → Vercel 배포된 Next.js가 그대로 표시.

- Vercel 배포 변경 = 앱 재배포 없이 즉시 반영
- 인터넷 필수
- 기존 localStorage JWT, Toss 결제, Kakao OAuth 모두 WebView 안에서 작동

---

## Kakao OAuth 주의

현재 redirect URI는 `https://www.sigak.asia/auth/kakao/callback`. WebView 안에서 Kakao 페이지로 이동 → 동의 후 redirect URI로 복귀. 정상 작동.

**만약 deep link(`sigak://`)를 쓰려면**:
1. Kakao Developer Console → Redirect URI에 `sigak://auth/kakao/callback` 추가
2. iOS `Info.plist` `CFBundleURLSchemes`에 `SIGAK` 추가
3. Android `AndroidManifest.xml`의 MainActivity에 intent-filter 추가
4. `@capacitor/app` 플러그인으로 `App.addListener('appUrlOpen', ...)` 처리

MVP는 https redirect만으로 충분. deep link는 post-MVP.

---

## 카메라 / 사진 업로드

현재 `<input type="file" accept="image/*">` 사용. WebView가 OS 네이티브 사진 피커를 자동으로 띄움 → 별도 플러그인 없이 작동.

더 풍부한 경험 원하면 `@capacitor/camera`:

```bash
pnpm add @capacitor/camera
npx cap sync
```

그리고 iOS `Info.plist` 권한 설명 추가:
```xml
<key>NSCameraUsageDescription</key>
<string>얼굴 사진을 업로드하기 위해 카메라를 사용합니다.</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>얼굴 사진을 업로드하기 위해 사진첩에 접근합니다.</string>
```

---

## 아이콘 / 스플래시

```bash
pnpm add -D @capacitor/assets
```

루트에 `assets/icon.png` (1024×1024) + `assets/splash.png` (2732×2732) 준비 후:

```bash
npx capacitor-assets generate
```

자동으로 모든 해상도 생성 + 네이티브 프로젝트에 배치.

---

## 정적 번들 모드로 전환 (Apple 심사 대비)

Apple은 순수 WebView 래퍼를 거부할 수 있습니다. 심사 시점에 전환:

### 1. Next.js 정적 export

`next.config.ts`:
```ts
const nextConfig = {
  output: 'export',
  images: { unoptimized: true },
};
```

### 2. 동적 라우트 확인

- `/verdict/[id]` 같은 dynamic route는 client-side fetch로 렌더하므로 문제 없음.
- `generateStaticParams` 없어도 `output: 'export'`에서 catch-all fallback으로 처리.
- 만약 빌드 에러 나면 해당 페이지에 `export const dynamic = 'force-static'` 또는 `dynamicParams = true`.

### 3. 빌드

```bash
pnpm build
```

→ `sigak-web/out/` 생성 (정적 HTML/JS/CSS).

### 4. Capacitor 설정 변경

`capacitor.config.ts`에서:
- `server.url` **제거**
- `webDir: 'out'` 유지

### 5. 동기화 + 재빌드

```bash
npx cap sync
pnpm cap:ios
```

→ 앱이 번들된 HTML을 로드. 오프라인 작동. API 호출만 인터넷 필요.

---

## `.gitignore` 예시

서버 모드 + 개발자마다 `cap add` 재실행 전제:

```gitignore
# Capacitor native platforms (재생성 가능)
sigak-web/ios/
sigak-web/android/
```

네이티브 프로젝트 커밋 방침이면 이 라인 빼고, Xcode/Android Studio 생성 파일은 포함.

---

## 배포

| 항목 | 값 |
|---|---|
| Bundle ID | `asia.sigak.app` |
| App 이름 | SIGAK |
| iOS 최소 타겟 | iOS 14.0 (Capacitor 6 기본) |
| Android 최소 SDK | 22 (Capacitor 6 기본) |

### App Store Connect
- Bundle ID 등록 → 인증서·프로비저닝 → Xcode에서 Archive → Upload
- 심사 시점: 순수 webview 거절 대응 (정적 번들 모드 전환 + 네이티브 기능 사용 명시)

### Google Play Console
- Keystore 생성 → `android/app/build.gradle`의 signingConfig 설정
- Android Studio → Build → Generate Signed Bundle
- Google Play에 업로드

---

## 알려진 한계 / 미정

- **Push 알림 (FCM)**: `@capacitor/push-notifications` + Firebase 프로젝트 생성 필요. 본인이 Firebase 설정 지시 주면 통합.
- **Deep link (kakao://)**: 서버 모드에서도 구현 가능하지만 Kakao Console + 네이티브 Info.plist/AndroidManifest 설정 필요. post-MVP.
- **SecureStorage**: 현재 localStorage JWT는 WebView 샌드박스 안이라 데이터 유출 리스크는 제한적. 진짜 보안이 필요하면 `@capacitor-community/secure-storage-plugin` 추가.
- **오프라인 지원**: 서버 모드는 인터넷 필수. 정적 번들 모드로 전환 시 일부 오프라인 가능(캐시된 화면). 완전 오프라인은 별도 엔지니어링.
