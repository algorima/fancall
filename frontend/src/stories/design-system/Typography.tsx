/**
 * TypeScale component displays a single typography scale with its properties.
 * @param {string} className - The Tailwind class for the type scale.
 * @param {string} description - Brief description of usage.
 */
function TypeScale({
  className,
  description,
}: {
  className: string;
  description: string;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-base-300 p-4">
      <div className="flex items-baseline justify-between gap-4">
        <span className={className}>The quick brown fox</span>
        <code className="text-body-s text-neutral">{className}</code>
      </div>
      <p className="text-label-m text-neutral">{description}</p>
    </div>
  );
}

/**
 * Typography component showcases the typography scales used in the design system.
 * It includes all 15 named type scales based on Material Design 3 conventions.
 */
export function Typography() {
  return (
    <div className="space-y-8">
      <section>
        <h2 className="mb-4 text-headline-s">Display</h2>
        <div className="space-y-3">
          <TypeScale
            className="text-display-l"
            description="히어로 섹션 (데스크톱)"
          />
          <TypeScale
            className="text-display-m"
            description="히어로 섹션 (모바일), 주요 섹션 제목 (데스크톱)"
          />
          <TypeScale
            className="text-display-s"
            description="주요 섹션 제목 (모바일)"
          />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-headline-s">Headline</h2>
        <div className="space-y-3">
          <TypeScale className="text-headline-l" description="서브섹션 제목" />
          <TypeScale className="text-headline-m" description="카드/모달 제목" />
          <TypeScale
            className="text-headline-s"
            description="본문 내 주요 제목"
          />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-headline-s">Title</h2>
        <div className="space-y-3">
          <TypeScale
            className="text-title-l"
            description="큰 제목 (FAQ, 인터랙티브)"
          />
          <TypeScale className="text-title-m" description="중간 제목" />
          <TypeScale className="text-title-s" description="소제목" />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-headline-s">Body</h2>
        <div className="space-y-3">
          <TypeScale
            className="text-body-l"
            description="인트로 텍스트, 강조 본문"
          />
          <TypeScale className="text-body-m" description="기본 본문" />
          <TypeScale
            className="text-body-s"
            description="보조 텍스트, Footer"
          />
        </div>
      </section>

      <section>
        <h2 className="mb-4 text-headline-s">Label</h2>
        <div className="space-y-3">
          <TypeScale className="text-label-l" description="버튼, 폼 라벨" />
          <TypeScale className="text-label-m" description="캡션, 메타 정보" />
          <TypeScale className="text-label-s" description="가장 작은 라벨" />
        </div>
      </section>
    </div>
  );
}
