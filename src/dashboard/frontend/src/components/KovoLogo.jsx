export default function KovoLogo({ size = 32, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`kovo-logo ${className}`}
      aria-label="Kovo logo"
    >
      {/* Antennae */}
      <line x1="24" y1="14" x2="20" y2="6" stroke="#378ADD" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="20" cy="5" r="2" fill="#378ADD" className="kovo-blink" />
      <line x1="40" y1="14" x2="44" y2="6" stroke="#378ADD" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="44" cy="5" r="2" fill="#378ADD" className="kovo-blink" />

      {/* Head */}
      <rect x="16" y="14" width="32" height="24" rx="8" fill="#378ADD" />

      {/* Eyes */}
      <ellipse cx="25" cy="24" rx="4" ry="5" fill="#042C53" />
      <ellipse cx="39" cy="24" rx="4" ry="5" fill="#042C53" />
      <circle cx="26" cy="23" r="1.5" fill="white" />
      <circle cx="40" cy="23" r="1.5" fill="white" />

      {/* Cheeks */}
      <ellipse cx="19" cy="30" rx="3" ry="2" fill="#6eb8ee" opacity="0.6" />
      <ellipse cx="45" cy="30" rx="3" ry="2" fill="#6eb8ee" opacity="0.6" />

      {/* Smile */}
      <path d="M26 33 Q32 37 38 33" stroke="#042C53" strokeWidth="2" strokeLinecap="round" fill="none" />

      {/* Body */}
      <rect x="20" y="38" width="24" height="18" rx="6" fill="#2d7bc4" />
      <rect x="26" y="42" width="12" height="8" rx="3" fill="#042C53" opacity="0.3" />

      {/* Arms */}
      <rect x="10" y="40" width="10" height="5" rx="2.5" fill="#2d7bc4" />
      <rect x="44" y="40" width="10" height="5" rx="2.5" fill="#2d7bc4" />
    </svg>
  )
}
