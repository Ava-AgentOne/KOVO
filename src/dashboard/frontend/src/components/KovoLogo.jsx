export default function KovoLogo({ size = 36, animate = true }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 120 120"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={animate ? 'kovo-breathe' : ''}
      aria-label="Kovo logo"
    >
      <rect width="120" height="120" rx="24" fill="#378ADD" />
      <line x1="48" y1="12" x2="42" y2="-8" stroke="#E6F1FB" strokeWidth="3" strokeLinecap="round" />
      <circle cx="42" cy="-12" r="5" fill="#E6F1FB" />
      <line x1="72" y1="12" x2="78" y2="-4" stroke="#E6F1FB" strokeWidth="3" strokeLinecap="round" />
      <circle cx="78" cy="-8" r="4.5" fill="#E6F1FB" />
      <g className={animate ? 'kovo-eyes' : ''} style={{ transformOrigin: '60px 52px' }}>
        <g transform="translate(44,52)">
          <ellipse rx="16" ry="17" fill="#FFF" />
          <circle cx="3" cy="1" r="9" fill="#042C53" />
          <circle cx="6" cy="-3" r="3" fill="#FFF" />
        </g>
        <g transform="translate(76,52)">
          <ellipse rx="16" ry="17" fill="#FFF" />
          <circle cx="3" cy="1" r="9" fill="#042C53" />
          <circle cx="6" cy="-3" r="3" fill="#FFF" />
        </g>
      </g>
      <path d="M52,78 Q60,85 68,78" fill="none" stroke="#E6F1FB" strokeWidth="2.5" strokeLinecap="round" />
      <ellipse cx="30" cy="70" rx="8" ry="5" fill="#F0997B" opacity="0.4" />
      <ellipse cx="90" cy="70" rx="8" ry="5" fill="#F0997B" opacity="0.4" />
    </svg>
  )
}
