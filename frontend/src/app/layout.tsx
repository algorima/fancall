import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Fancall - AI-powered Video Call",
  description: "AI-powered video call with virtual companions",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
