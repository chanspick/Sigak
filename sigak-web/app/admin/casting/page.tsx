import { Suspense } from "react";
import { CastingPool } from "@/components/admin/casting-pool";

export default function CastingPoolPage() {
  return (
    <Suspense>
      <CastingPool />
    </Suspense>
  );
}
