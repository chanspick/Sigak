// 폴링 유틸리티 (30초 간격 + visibilitychange 중지)

interface PollingOptions {
  interval?: number;
  onData: (data: unknown) => void;
  onError?: (error: Error) => void;
}

/** 30초 폴링 시작 (탭 비활성시 자동 중지) */
export function startPolling(
  fetchFn: () => Promise<unknown>,
  options: PollingOptions,
): () => void {
  const { interval = 30000, onData, onError } = options;
  let timer: ReturnType<typeof setInterval> | null = null;
  let isActive = true;

  const poll = async () => {
    if (!isActive) return;
    try {
      const data = await fetchFn();
      onData(data);
    } catch (err) {
      onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  };

  const start = () => {
    if (timer) return;
    poll();
    timer = setInterval(poll, interval);
  };

  const stop = () => {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  };

  // visibilitychange 핸들러
  const handleVisibility = () => {
    if (document.hidden) {
      stop();
    } else {
      start();
    }
  };

  document.addEventListener("visibilitychange", handleVisibility);
  start();

  // 정리 함수 반환
  return () => {
    isActive = false;
    stop();
    document.removeEventListener("visibilitychange", handleVisibility);
  };
}
