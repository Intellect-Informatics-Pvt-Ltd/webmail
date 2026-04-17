/**
 * PSense Mail — Query context hook.
 *
 * Provides a KeyContext (tenantId + accountId) for all query key factories.
 * In v1.1 (Phase 1), tenantId defaults to "default" and accountId defaults
 * to the auth user's ID. Phase 4 (multi-account) updates this.
 */

import { createContext, useContext, type ReactNode } from "react";
import { type KeyContext } from "./keys";

const QueryContext = createContext<KeyContext>({
  tenantId: "default",
  accountId: "default",
});

export function QueryContextProvider({
  children,
  tenantId = "default",
  accountId = "default",
}: {
  children: ReactNode;
  tenantId?: string;
  accountId?: string;
}) {
  return (
    <QueryContext.Provider value={{ tenantId, accountId }}>
      {children}
    </QueryContext.Provider>
  );
}

export function useQueryContext(): KeyContext {
  return useContext(QueryContext);
}
