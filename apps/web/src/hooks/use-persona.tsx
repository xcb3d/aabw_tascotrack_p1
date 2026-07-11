import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { identityService } from "@/services/mock-services";
import type { User } from "@/types";

interface PersonaContextValue { persona: User | null; personas: User[]; switchPersona: (id: string) => Promise<void> }
const PersonaContext = createContext<PersonaContextValue | null>(null);

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [persona, setPersona] = useState<User | null>(null);
  const [personas, setPersonas] = useState<User[]>([]);
  const queryClient = useQueryClient();

  const loadPersona = () => {
    identityService.getCurrentPersona().then((current) => {
      setPersona(current);
    });
  };

  useEffect(() => {
    identityService.getPersonas().then((list) => {
      setPersonas(list);
    });
    loadPersona();

    const handleAuthChange = () => {
      loadPersona();
      localStorage.removeItem("tasco-session-id");
      queryClient.clear();
    };

    window.addEventListener("tasco-auth-changed", handleAuthChange);
    window.addEventListener("storage", handleAuthChange);

    return () => {
      window.removeEventListener("tasco-auth-changed", handleAuthChange);
      window.removeEventListener("storage", handleAuthChange);
    };
  }, [queryClient]);

  const switchPersona = async (id: string) => {
    const next = await identityService.switchPersona(id);
    localStorage.removeItem("tasco-session-id");
    setPersona(next);
    await queryClient.invalidateQueries();
  };

  return <PersonaContext.Provider value={{ persona, personas, switchPersona }}>{children}</PersonaContext.Provider>;
}

export function usePersona() { const context = useContext(PersonaContext); if (!context) throw new Error("usePersona must be used inside PersonaProvider"); return context; }
