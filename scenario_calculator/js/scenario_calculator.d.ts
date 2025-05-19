import { FormUpdateOptions } from "./scenario_calculator";
declare global {
  interface Window {
    formUpdate: (
      clickedElement?: HTMLSelectElement | HTMLInputElement,
      options?: FormUpdateOptions
    ) => void;
    choosePoint: (event: MouseEvent) => void;
    closeAreaPanel: () => void;
    updateParams: () => void;
    searchHere: () => void;
    zoomToRegions: () => void;
    zoomToEvent: () => void;
    zoomToAllEvents: () => void;
    calculateImpact: () => void;
    setFilters: () => Promise<void>;
    toggleTable: (key: string) => void;
    sortColumn: (key: string, direction: "up" | "down") => void;
  }
}
