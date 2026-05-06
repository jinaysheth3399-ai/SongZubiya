/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(214, 32%, 91%)',
        background: 'hsl(0, 0%, 100%)',
        foreground: 'hsl(222, 47%, 11%)',
        muted: 'hsl(210, 40%, 96%)',
        'muted-foreground': 'hsl(215, 16%, 47%)',
        primary: 'hsl(222, 47%, 11%)',
        'primary-foreground': 'hsl(210, 40%, 98%)',
        accent: 'hsl(210, 40%, 94%)',
        destructive: 'hsl(0, 84%, 60%)',
        success: 'hsl(142, 70%, 45%)',
        warning: 'hsl(38, 92%, 50%)',
      },
    },
  },
  plugins: [],
}
