export const metadata = {
  title: 'KR DATA CHAT',
  description: 'Chat with your Supabase data'
}

export default function RootLayout({ children }) {
  return (
    <html lang='en'>
      <body style={{ margin: 0, fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto' }}>
        {children}
      </body>
    </html>
  )
}
