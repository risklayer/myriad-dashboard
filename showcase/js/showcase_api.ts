import { identity, memoize, sortBy } from "lodash";
import createClient from "openapi-fetch";
import {
  ApiPaths,
  DataTableColumnSchema,
  FeatureCollectionSchema,
  ShapeFeature,
  type CountriesEnum,
  type Nuts3AreaSchema,
  type paths,
} from "../../data/types/api";

export const client = createClient<paths>();

export const getShapesList = memoize(
  async function getShapesList(
    countries: CountriesEnum | CountriesEnum[]
  ): Promise<ShapeFeature[] | null> {
    if (Array.isArray(countries)) {
      return (
        await Promise.all(countries.map((country) => getShapesList(country)))
      )
        .flat(1)
        .filter((val) => val != null);
    }
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(ApiPaths.data_v1_areas_shapes, {
      params: {
        query: { countries: [countries] },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the area outlines.");
      console.error(error);
      return null;
    }
    const shapes = data.features;
    return shapes;
  },
  (countries: string | string[]) => sortBy([countries].flat(), identity).join()
);

export const getAreasMap = memoize(
  async function getAreasMap(
    countries: CountriesEnum | CountriesEnum[],
    bbox?: string
  ): Promise<Record<string, Nuts3AreaSchema> | null> {
    if (Array.isArray(countries)) {
      return (
        await Promise.all(countries.map((country) => getAreasMap(country)))
      ).reduce((acc, areas) => ({ ...acc, ...areas }), {});
    }
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(ApiPaths.data_v1_areas_map, {
      params: {
        query: { countries: [countries], bbox },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the area outlines.");
      console.error(error);
      return null;
    }
    return data;
  },
  (countries: string | string[], bbox?: string) =>
    [sortBy([countries].flat(), identity), bbox].flat().join()
);

export const getValuesMap = memoize(
  async function getValuesMap(
    countries: CountriesEnum[],
    columns: string[] | string
  ): Promise<Record<string, Record<string, number>> | null> {
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(ApiPaths.data_v1_values_values, {
      params: {
        query: { countries, columns: [columns].flat() },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the data.");
      console.error(error);
      return null;
    }
    return data;
  },
  (countries: string[], columns: string[] | string) =>
    [sortBy([countries].flat(), identity), sortBy([columns].flat(), identity)]
      .flat()
      .join()
);

export const getColumnsMap = memoize(
  async function getColumnsMap(
    columns: string[] | string
  ): Promise<Record<string, DataTableColumnSchema> | null> {
    if (!columns?.length) {
      return {};
    }
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(ApiPaths.data_v1_columns_columns_map, {
      params: {
        query: { columns: [columns].flat() },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving dataset details.");
      console.error(error);
      return null;
    }
    return data;
  },
  (columns: string[] | string) => sortBy([columns].flat(), identity).join()
);

export async function downloadGeoJSON({
  countries,
  areas,
  columns,
}: {
  countries?: CountriesEnum[] | CountriesEnum;
  areas?: string[] | string;
  columns?: string[] | string;
}): Promise<FeatureCollectionSchema | null> {
  const {
    data, // only present if 2XX response
    error, // only present if 4XX or 5XX response
  } = await client.GET(ApiPaths.data_v1_areas_shapes, {
    params: {
      query: {
        countries: [countries!].flat().filter(Boolean),
        columns: [columns!].flat().filter(Boolean),
        nuts3areas: [areas!].flat().filter(Boolean),
      },
    },
  });
  if (error) {
    window.toast("Sorry, there was a problem retrieving dataset details.");
    console.error(error);
    return null;
  }
  return data;
}
