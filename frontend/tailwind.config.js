/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                primary: {
                    DEFAULT: "#10B981",
                    hover: "#059669",
                    light: "#34D399",
                },
                secondary: {
                    DEFAULT: "#3B82F6",
                    hover: "#2563EB",
                },
                background: "#FFFFFF",
                surface: "#F9FAFB",
                border: "#E5E7EB",
                text: {
                    primary: "#111827",
                    secondary: "#4B5563",
                    muted: "#9CA3AF",
                },
            },
            fontFamily: {
                sans: ["Plus Jakarta Sans", "Inter", "system-ui", "sans-serif"],
            },
            borderRadius: {
                'lg': '0.75rem',
                'md': '0.5rem',
                'sm': '0.375rem',
                'xl': '1rem',
                '2xl': '1.25rem',
            },
            boxShadow: {
                'sm': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
                'DEFAULT': '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)',
                'md': '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)',
                'lg': '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)',
            },
        },
    },
    plugins: [require("tailwindcss-animate")],
}
