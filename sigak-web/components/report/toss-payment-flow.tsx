"use client";

// 토스페이먼츠 결제 위젯 플로우
// - SDK v2 로드
// - 결제 위젯 렌더링 (결제 수단 선택 + 약관 동의)
// - requestPayment → successUrl/failUrl 리다이렉트

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";

interface TossPaymentFlowProps {
  orderId: string;
  orderName: string;
  amount: number;
  customerName?: string;
  customerEmail?: string;
}

declare global {
  interface Window {
    TossPayments?: (clientKey: string) => {
      widgets: (options: { customerKey: string }) => {
        setAmount: (params: { currency: string; value: number }) => Promise<void>;
        renderPaymentMethods: (params: { selector: string; variantKey?: string }) => Promise<void>;
        renderAgreement: (params: { selector: string; variantKey?: string }) => Promise<void>;
        requestPayment: (params: {
          orderId: string;
          orderName: string;
          successUrl: string;
          failUrl: string;
          customerName?: string;
          customerEmail?: string;
        }) => Promise<void>;
      };
    };
  }
}

const TOSS_CLIENT_KEY = process.env.NEXT_PUBLIC_TOSS_CLIENT_KEY || "test_gck_yL0qZ4G1VO54GNy9Wnjo8oWb2MQY";

export function TossPaymentFlow({
  orderId,
  orderName,
  amount,
  customerName,
  customerEmail,
}: TossPaymentFlowProps) {
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const widgetsRef = useRef<ReturnType<ReturnType<NonNullable<Window["TossPayments"]>>["widgets"]> | null>(null);
  const initRef = useRef(false);

  // SDK 로드 + 위젯 초기화
  useEffect(() => {
    if (initRef.current) return;
    initRef.current = true;

    const loadSDK = () => {
      return new Promise<void>((resolve, reject) => {
        if (window.TossPayments) {
          resolve();
          return;
        }
        const script = document.createElement("script");
        script.src = "https://js.tosspayments.com/v2/standard";
        script.onload = () => resolve();
        script.onerror = () => reject(new Error("토스페이먼츠 SDK 로드 실패"));
        document.head.appendChild(script);
      });
    };

    (async () => {
      try {
        await loadSDK();

        if (!window.TossPayments) {
          throw new Error("토스페이먼츠 SDK를 초기화할 수 없습니다");
        }

        const tossPayments = window.TossPayments(TOSS_CLIENT_KEY);
        const widgets = tossPayments.widgets({ customerKey: "ANONYMOUS" });

        await widgets.setAmount({ currency: "KRW", value: amount });
        await widgets.renderPaymentMethods({ selector: "#toss-payment-method", variantKey: "DEFAULT" });
        await widgets.renderAgreement({ selector: "#toss-agreement", variantKey: "AGREEMENT" });

        widgetsRef.current = widgets;
        setReady(true);
      } catch (err) {
        setError(err instanceof Error ? err.message : "결제 위젯 로드 실패");
      }
    })();
  }, [amount]);

  const handlePayment = async () => {
    if (!widgetsRef.current) return;
    setLoading(true);

    try {
      const origin = window.location.origin;
      await widgetsRef.current.requestPayment({
        orderId,
        orderName,
        successUrl: `${origin}/payment/success`,
        failUrl: `${origin}/payment/fail`,
        customerName: customerName || undefined,
        customerEmail: customerEmail || undefined,
      });
    } catch (err) {
      setLoading(false);
      // 사용자가 결제창을 닫은 경우
      if (err instanceof Error && err.message.includes("USER_CANCEL")) {
        return;
      }
      setError(err instanceof Error ? err.message : "결제 요청 실패");
    }
  };

  if (error) {
    return (
      <div className="border border-[var(--color-line)] rounded-lg p-6 max-w-sm mx-auto text-center">
        <p className="text-sm text-red-500 mb-4">{error}</p>
        <Button variant="primary" size="md" onClick={() => window.location.reload()}>
          다시 시도
        </Button>
      </div>
    );
  }

  return (
    <div className="max-w-sm mx-auto">
      {/* 토스 결제 수단 선택 영역 */}
      <div id="toss-payment-method" className="mb-4" />

      {/* 약관 동의 영역 */}
      <div id="toss-agreement" className="mb-4" />

      {/* 결제 버튼 */}
      <Button
        variant="primary"
        size="lg"
        className="w-full rounded-lg"
        onClick={handlePayment}
        disabled={!ready || loading}
      >
        {!ready ? "결제 준비 중..." : loading ? "결제 진행 중..." : `₩${amount.toLocaleString()} 결제하기`}
      </Button>
    </div>
  );
}
