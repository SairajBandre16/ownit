/**
 * Local-first persistence in IndexedDB (idb-keyval). Nothing is stored server-side.
 *
 * Stores: documents, style profile, revision deck, progress history, settings.
 */
import { createStore, del, get, keys, set, values } from "idb-keyval";
import type { OwnDoc } from "./types";

const isBrowser = typeof indexedDB !== "undefined";

const docStore = () => createStore("ownit-docs", "docs");
const metaStore = () => createStore("ownit-meta", "kv");

let _docs: ReturnType<typeof createStore> | null = null;
let _meta: ReturnType<typeof createStore> | null = null;
const docs = () => (_docs ??= docStore());
const meta = () => (_meta ??= metaStore());

export async function listDocs(): Promise<OwnDoc[]> {
  if (!isBrowser) return [];
  const all = (await values<OwnDoc>(docs())) ?? [];
  return all.sort((a, b) => b.updatedAt - a.updatedAt);
}

export async function getDoc(id: string): Promise<OwnDoc | undefined> {
  if (!isBrowser) return undefined;
  return get<OwnDoc>(id, docs());
}

export async function saveDoc(doc: OwnDoc): Promise<void> {
  if (!isBrowser) return;
  await set(doc.id, { ...doc, updatedAt: Date.now() }, docs());
}

export async function deleteDoc(id: string): Promise<void> {
  if (!isBrowser) return;
  await del(id, docs());
}

export async function docIds(): Promise<string[]> {
  if (!isBrowser) return [];
  return (await keys(docs())) as string[];
}

export async function getMeta<T>(key: string): Promise<T | undefined> {
  if (!isBrowser) return undefined;
  return get<T>(key, meta());
}

export async function setMeta<T>(key: string, value: T): Promise<void> {
  if (!isBrowser) return;
  await set(key, value, meta());
}

export function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}
