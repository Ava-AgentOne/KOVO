export default function KovoLogo({ size = 36, animate = true }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="-3 -6 126 140"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={animate ? 'kovo-logo' : ''}
      aria-label="Kovo logo"
    >
      {/* Antennae */}
      <line x1="48" y1="22" x2="42" y2="2" stroke="#378ADD" strokeWidth="3" strokeLinecap="round" />
      <circle cx="42" cy="0" r="5" fill="#85B7EB" className={animate ? 'kovo-blink' : ''} />
      <line x1="72" y1="22" x2="78" y2="6" stroke="#378ADD" strokeWidth="3" strokeLinecap="round" />
      <circle cx="78" cy="4" r="4.5" fill="#85B7EB" className={animate ? 'kovo-blink' : ''} />

      {/* Head */}
      <rect x="10" y="20" width="100" height="100" rx="24" fill="#378ADD" />

      {/* Eyes — clipPath hides overflow for blink effect */}
      <defs>
        <clipPath id="leftEyeClip">
          <ellipse cx="40" cy="60" rx="18" ry="19" />
        </clipPath>
        <clipPath id="rightEyeClip">
          <ellipse cx="80" cy="60" rx="18" ry="19" />
        </clipPath>
      </defs>

      {/* Left eye */}
      <g>
        {/* White */}
        <ellipse cx="40" cy="60" rx="18" ry="19" fill="#FFF" />
        {/* Pupil group — moves left/right */}
        <g clipPath="url(#leftEyeClip)" className={animate ? 'kovo-pupil' : ''} style={{ transformOrigin: '40px 60px' }}>
          <circle cx="44" cy="62" r="10" fill="#042C53" />
          <circle cx="47" cy="57" r="4" fill="#FFF" />
          <circle cx="40" cy="66" r="2" fill="#FFF" />
        </g>
        {/* Eyelid — slides down to blink */}
        <rect
          x="22" y="41"
          width="36" height="38"
          rx="12"
          fill="#378ADD"
          clipPath="url(#leftEyeClip)"
          className={animate ? 'kovo-eyelid-left' : ''}
        />
      </g>

      {/* Right eye */}
      <g>
        {/* White */}
        <ellipse cx="80" cy="60" rx="18" ry="19" fill="#FFF" />
        {/* Pupil group — moves left/right */}
        <g clipPath="url(#rightEyeClip)" className={animate ? 'kovo-pupil' : ''} style={{ transformOrigin: '80px 60px' }}>
          <circle cx="84" cy="62" r="10" fill="#042C53" />
          <circle cx="87" cy="57" r="4" fill="#FFF" />
          <circle cx="80" cy="66" r="2" fill="#FFF" />
        </g>
        {/* Eyelid — slides down to blink */}
        <rect
          x="62" y="41"
          width="36" height="38"
          rx="12"
          fill="#378ADD"
          clipPath="url(#rightEyeClip)"
          className={animate ? 'kovo-eyelid-right' : ''}
        />
      </g>

      {/* Smile */}
      <path d="M48,90 Q60,100 72,90" fill="none" stroke="#E6F1FB" strokeWidth="3" strokeLinecap="round" />

      {/* Rosy cheeks */}
      <ellipse cx="26" cy="82" rx="9" ry="6" fill="#F0997B" opacity="0.45" />
      <ellipse cx="94" cy="82" rx="9" ry="6" fill="#F0997B" opacity="0.45" />
    </svg>
  )
}
