"use client";

import { useCallback, useEffect, useState } from "react";
import type { StyleProfile } from "@/lib/api";
import { getMeta, setMeta } from "@/lib/db";

export interface StoredProfile {
  profile: StyleProfile;
  samples: string[];
  createdAt: number;
}

const KEY = "styleProfile";

/** The student's Voice Fingerprint (U1), stored locally in IndexedDB. */
export function useStyleProfile() {
  const [stored, setStored] = useState<StoredProfile | null | undefined>(undefined);
  useEffect(() => {
    getMeta<StoredProfile>(KEY).then((p) => setStored(p ?? null));
  }, []);
  const save = useCallback(async (p: StoredProfile | null) => {
    await setMeta(KEY, p);
    setStored(p);
  }, []);
  return { stored, loading: stored === undefined, save };
}
