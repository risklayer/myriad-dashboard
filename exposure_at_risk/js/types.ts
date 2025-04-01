import { Nuts2AreaSchema } from "../../data/types/api";

export type TableDatum = {
  region: Nuts2AreaSchema;
} & { [code: string]: number };
