/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'deep-space': '#030303',
        'canvas-white': '#ffffff',
        'system-gray': '#e5e7eb',
        'terminal-green': '#73ffb9',
        brand: {
          50:  '#f0f0ff',
          100: '#e0e0ff',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          900: '#1e1b4b',
        },
        surface: {
          900: '#0a0a14',
          800: '#0f0f1e',
          700: '#161628',
          600: '#1e1e32',
          500: '#26263c',
          400: '#2e2e48',
        },
      },
      fontFamily: {
        'pp-neue-montreal': ['PP Neue Montreal', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        lg: '8.64px',
        full: '9999px',
      },
      spacing: {
        'spacing-4': '4px',
        'spacing-8': '8px',
        'spacing-12': '12px',
        'spacing-16': '16px',
        'spacing-20': '20px',
        'spacing-28': '28px',
        'spacing-32': '32px',
        'spacing-36': '36px',
        'spacing-40': '40px',
        'spacing-48': '48px',
        'spacing-56': '56px',
        'spacing-60': '60px',
        'spacing-80': '80px',
        'spacing-112': '112px',
      },
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow':       'glow 2s ease-in-out infinite alternate',
        'slide-in':   'slideIn 0.3s ease-out',
        'fade-in':    'fadeIn 0.4s ease-out',
      },
      keyframes: {
        glow: {
          '0%':   { boxShadow: '0 0 5px #6366f1, 0 0 10px #6366f1' },
          '100%': { boxShadow: '0 0 15px #6366f1, 0 0 30px #6366f1, 0 0 45px #6366f1' },
        },
        slideIn: {
          from: { transform: 'translateY(8px)', opacity: '0' },
          to:   { transform: 'translateY(0)',   opacity: '1' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
      },
      backdropBlur: { xs: '2px' },
    },
  },
  plugins: [],
}
