"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ServerStatus } from "./ServerStatus";
import { ThemeToggle } from "./ThemeToggle";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/workspace", label: "Workspace" },
  { href: "/voice", label: "Voice" },
  { href: "/deck", label: "Deck" },
  { href: "/progress", label: "Progress" },
  { href: "/learn", label: "Learn" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="sticky top-0 z-40 border-b border-rule bg-background/85 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4 sm:px-6">
        <Link href="/" className="flex items-baseline gap-1.5" aria-label="OwnIt v0.1 home">
          <span className="font-display text-2xl leading-none">OwnIt</span>
          <span className="tabular text-[10px] text-muted-foreground">v0.1</span>
        </Link>
        <nav aria-label="Main" className="hidden items-center gap-1 sm:flex">
          {NAV.map((item) => {
            const active = pathname?.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                prefetch={false}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "rounded-md px-2.5 py-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground",
                  active && "bg-secondary text-foreground",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <span className="hidden rounded-full border border-rule px-2.5 py-0.5 text-xs text-muted-foreground md:inline tabular">
            0 AI models · 0 external APIs
          </span>
          <ServerStatus />
          <ThemeToggle />
        </div>
      </div>
      <nav aria-label="Main mobile" className="flex gap-1 overflow-x-auto border-t border-rule px-4 py-1.5 sm:hidden">
        {NAV.map((item) => (
          <Link key={item.href} href={item.href} prefetch={false} className="shrink-0 rounded-md px-2 py-1 text-sm text-muted-foreground">
            {item.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
