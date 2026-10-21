/** @type {import('tailwindcss').Config} */
module.exports = {
    darkMode: ["selector", '[data-theme="dark"]'],
    content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./app/**/*.{ts,tsx}"
  ],
  theme: {
  	extend: {
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
  		colors: {
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			desk: 'hsl(var(--desk) / <alpha-value>)',
  			paper: 'hsl(var(--paper) / <alpha-value>)',
  			'paper-2': 'hsl(var(--paper-2) / <alpha-value>)',
  			line: 'hsl(var(--line) / <alpha-value>)',
  			'line-strong': 'hsl(var(--line-strong) / <alpha-value>)',
  			margin: 'hsl(var(--margin) / <alpha-value>)',
  			ink: 'hsl(var(--ink) / <alpha-value>)',
  			'ink-soft': 'hsl(var(--ink-soft) / <alpha-value>)',
  			pen: 'hsl(var(--pen) / <alpha-value>)',
  			'pen-fg': 'hsl(var(--pen-fg) / <alpha-value>)',
  			hl: 'hsl(var(--hl) / <alpha-value>)',
  			'hl-fg': 'hsl(var(--hl-fg) / <alpha-value>)',
  			amber: 'hsl(var(--amber) / <alpha-value>)',
  			red: 'hsl(var(--red) / <alpha-value>)',
  			tape: 'var(--tape)',
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		fontFamily: {
  			display: ['var(--font-serif)', 'Georgia', 'serif'],
  			sans: ['var(--font-sans)', 'system-ui', 'sans-serif'],
  			serif: ['var(--font-serif)', 'Georgia', 'serif'],
  			hand: ['var(--font-serif)', 'Georgia', 'serif'],
  			mono: ['var(--font-mono)', 'ui-monospace', 'monospace']
  		},
  		// Editorial contract: two weights only. `font-bold` across older pages renders at 500.
  		fontWeight: {
  			bold: '500'
  		},
  		boxShadow: {
  			paper: 'var(--shadow)',
  			float: 'var(--shadow-float)'
  		},
  		keyframes: {
  			'accordion-down': {
  				from: {
  					height: '0'
  				},
  				to: {
  					height: 'var(--radix-accordion-content-height)'
  				}
  			},
  			'accordion-up': {
  				from: {
  					height: 'var(--radix-accordion-content-height)'
  				},
  				to: {
  					height: '0'
  				}
  			}
  		},
  		animation: {
  			'accordion-down': 'accordion-down 0.2s ease-out',
  			'accordion-up': 'accordion-up 0.2s ease-out'
  		}
  	}
  },
  plugins: [require("tailwindcss-animate")],
};