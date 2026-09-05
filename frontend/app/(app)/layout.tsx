import Sidebar from "@/components/Sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <main
        style={{
          flex: 1,
          padding: "32px 36px",
          minWidth: 0,
          maxWidth: 1200,
        }}
      >
        {children}
      </main>
    </div>
  );
}
