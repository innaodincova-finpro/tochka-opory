// Проверка доступа к кабинету «Точка опоры». Сведений о клиентах сюда не приходит:
// только код доступа и случайная метка устройства.
import { createClient } from "npm:@supabase/supabase-js@2";
const ADMIN_HASH = "b0efd402ee10bf5ed139f6c290707e9db93faa3b9b565ab3b6ee574e223507b0";
const A = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, authorization, apikey, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
const out = (o: unknown, s = 200) => new Response(JSON.stringify(o), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
const norm = (s: unknown) => String(s || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
const fmt = (s: string) => s.slice(0, 4) + "-" + s.slice(4, 8);
async function sha(t: string) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(t));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}
function newCode() {
  const r = crypto.getRandomValues(new Uint8Array(8));
  return fmt([...r].map((x) => A[x % 32]).join(""));
}
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return out({ ok: false, reason: "method" }, 405);
  let b: any = {};
  try { b = await req.json(); } catch { return out({ ok: false, reason: "bad" }, 400); }
  const act = String(b.action || "");
  if (act === "check") {
    const n = norm(b.code), device = String(b.device || "").slice(0, 64), kind = String(b.kind || "").slice(0, 40);
    if (n.length !== 8 || device.length < 8) return out({ ok: false, reason: "bad" });
    const code = fmt(n);
    const { data: c } = await db.from("opora_codes").select("code,disabled,max_devices").eq("code", code).maybeSingle();
    if (!c) { await db.from("opora_attempts").insert({ code, device, kind, result: "нет такого кода" }); return out({ ok: false, reason: "bad" }); }
    if (c.disabled) { await db.from("opora_attempts").insert({ code, device, kind, result: "код отключён" }); return out({ ok: false, reason: "off" }); }
    const { data: d } = await db.from("opora_devices").select("device").eq("code", code);
    const list = d || [];
    if (list.some((x: any) => x.device === device)) {
      await db.from("opora_devices").update({ last_at: new Date().toISOString(), kind }).eq("code", code).eq("device", device);
      return out({ ok: true, code });
    }
    if (list.length >= c.max_devices) { await db.from("opora_attempts").insert({ code, device, kind, result: "лишнее устройство" }); return out({ ok: false, reason: "limit" }); }
    await db.from("opora_devices").insert({ code, device, kind });
    return out({ ok: true, code });
  }
  // Действия автора: нужен пароль страницы управления.
  if ((await sha("opora-admin|" + String(b.pass || "").trim().toUpperCase())) !== ADMIN_HASH) return out({ ok: false, reason: "pass" }, 403);
  if (act === "list") {
    const [{ data: codes }, { data: devs }, { data: att }] = await Promise.all([
      db.from("opora_codes").select("*").order("created_at", { ascending: false }),
      db.from("opora_devices").select("*"),
      db.from("opora_attempts").select("*").order("at", { ascending: false }).limit(50),
    ]);
    return out({ ok: true, codes: codes || [], devices: devs || [], attempts: att || [] });
  }
  if (act === "issue") {
    for (let i = 0; i < 5; i++) {
      const code = newCode();
      const { error } = await db.from("opora_codes").insert({ code, label_enc: String(b.label || "").slice(0, 2000) });
      if (!error) return out({ ok: true, code });
    }
    return out({ ok: false, reason: "issue" }, 500);
  }
  const code = fmt(norm(b.code));
  if (act === "disable" || act === "enable") {
    await db.from("opora_codes").update({ disabled: act === "disable" }).eq("code", code);
    return out({ ok: true });
  }
  if (act === "reset") { await db.from("opora_devices").delete().eq("code", code); return out({ ok: true }); }
  if (act === "label") { await db.from("opora_codes").update({ label_enc: String(b.label || "").slice(0, 2000) }).eq("code", code); return out({ ok: true }); }
  if (act === "delete") { await db.from("opora_codes").delete().eq("code", code); return out({ ok: true }); }
  return out({ ok: false, reason: "action" }, 400);
});
