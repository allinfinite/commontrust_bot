import { NextResponse } from "next/server";

import { adminCookieName } from "@/lib/admin_auth";

export const runtime = "nodejs";

export async function POST() {
  const res = NextResponse.redirect("/admin/login", { status: 303 });
  res.cookies.set({
    name: adminCookieName(),
    value: "",
    httpOnly: true,
    secure: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0
  });
  return res;
}

