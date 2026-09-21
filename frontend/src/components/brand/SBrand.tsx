/**
 * Subly S-Mark — özel amblem (emerald gradient).
 * Uygulamanın her yerinde <SBrand /> olarak kullanılır. `size` ve `rounded` parametreleri
 * sidebar (11), login hero (40), topbar (36) gibi farklı yerleşimlere göre ayarlanır.
 */
type Props = {
  size?: number;
  rounded?: "md" | "lg" | "xl" | "2xl";
  className?: string;
};

const roundedClass: Record<NonNullable<Props["rounded"]>, string> = {
  md: "rounded-md",
  lg: "rounded-lg",
  xl: "rounded-xl",
  "2xl": "rounded-2xl",
};

export function SBrand({ size = 36, rounded = "xl", className = "" }: Props) {
  return (
    <span
      className={`relative inline-grid shrink-0 place-items-center overflow-hidden ${roundedClass[rounded]} ${className}`}
      style={{ width: size, height: size }}
      data-testid="subly-brand-mark"
      aria-hidden="true"
    >
      <svg viewBox="0 0 40 40" width={size} height={size} xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="subly-brand-bg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#10B981" />
            <stop offset="55%" stopColor="#059669" />
            <stop offset="100%" stopColor="#0d9488" />
          </linearGradient>
          <linearGradient id="subly-brand-fg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#F0FDF4" />
            <stop offset="100%" stopColor="#FFFFFF" />
          </linearGradient>
        </defs>
        <rect x="0" y="0" width="40" height="40" rx="10" fill="url(#subly-brand-bg)" />
        {/* soft top-light for depth */}
        <path d="M0 0 H40 V16 C24 22, 16 22, 0 16 Z" fill="#ffffff" fillOpacity="0.10" />
        {/* Stylised S — two mirrored arcs with a diagonal cut */}
        <path
          d="M28.5 12.6c-1.2-2.4-3.9-4-7.3-4-4.5 0-7.8 2.3-7.8 5.7 0 3 2.3 4.5 6.1 5.4l3.2.8c2.9.7 4.2 1.5 4.2 3 0 1.8-2 3-4.7 3-2.7 0-4.7-1.1-5.6-3.1"
          fill="none"
          stroke="url(#subly-brand-fg)"
          strokeWidth="3"
          strokeLinecap="round"
        />
        {/* tiny accent dot */}
        <circle cx="30" cy="10" r="1.9" fill="#A7F3D0" />
      </svg>
    </span>
  );
}
