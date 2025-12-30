import { useTranslation } from "react-i18next";

import { FANCALL_NS } from "@/i18n";

interface StartCallSectionProps {
  onStart: () => void;
  isLoading: boolean;
}

export function StartCallSection({
  onStart,
  isLoading,
}: StartCallSectionProps) {
  const { t } = useTranslation(FANCALL_NS);

  return (
    <div className="w-full lg:max-w-[720px]">
      <h1 className="mb-2 text-left text-3xl font-bold text-base-content sm:mb-8 sm:text-center sm:text-4xl md:mb-8">
        {t("entry.title")}
      </h1>
      <p className="mb-4 text-left text-sm text-base-content/70 sm:mb-8 sm:text-center sm:text-base md:mb-16">
        {t("entry.subtitle")}
      </p>

      <div className="flex justify-center">
        <button
          onClick={onStart}
          disabled={isLoading}
          className="btn btn-neutral h-16 min-w-48 text-base font-medium text-neutral-content"
        >
          {isLoading ? (
            <span className="loading loading-spinner loading-sm" />
          ) : (
            t("entry.startCall")
          )}
        </button>
      </div>
    </div>
  );
}
