import { Nuts3AreaSchema } from "../../data/types/api";

export type TableDatum = {
  region: Nuts3AreaSchema;
} & { [code: string]: number };
