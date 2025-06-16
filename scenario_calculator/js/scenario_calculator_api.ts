import { identity, sortBy } from "lodash";
import createClient from "openapi-fetch";
import {
  ApiPaths,
  FeatureCollectionSchema,
  HrscEventSchema,
  ShapeFeature,
  type CountriesEnum,
  type Nuts3AreaSchema,
  type paths,
} from "../../data/types/api";
import { memoizeUnlessNull } from "../../shared/js/utils";

export const client = createClient<paths>();

export const getShapesList = memoizeUnlessNull(
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

export const getEventDetail = memoizeUnlessNull(
  async function getEventDetail(
    ids: number | number[]
  ): Promise<HrscEventSchema[]> {
    if (Array.isArray(ids)) {
      return (await Promise.all(ids.map((id) => getEventDetail(id))))
        .flat(1)
        .filter((val) => val != null);
    }
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET("/data/api/v1/hrsc/event/{id}/detail", {
      params: {
        path: { id: ids as number },
      },
    });
    if (error) {
      window.toast("Sorry, there was a problem retrieving the area outlines.");
      console.error(error);
      return [];
    }
    return [data].filter(Boolean);
  },
  (ids: number | number[]) => sortBy([ids].flat(), identity).join()
);
export const getAreasMap = memoizeUnlessNull(
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

export const getCombinedImpact = memoizeUnlessNull(
  async function getCombinedImpact(
    eventIds: number[],
    bbox: string,
    countries: CountriesEnum | CountriesEnum[],
    exposure_key: string
  ): Promise<FeatureCollectionSchema | null> {
    const {
      data, // only present if 2XX response
      error, // only present if 4XX or 5XX response
    } = await client.GET(
      "/data/api/v1/hrsc/scenario/calculate_impact/{exposure_key}",
      {
        params: {
          query: {
            event_ids: eventIds,
            include_geometry: false,
            bbox,
            countries: countries as CountriesEnum[],
          },
          path: {
            exposure_key,
          },
        },
      }
    );
    if (error) {
      window.toast(
        `Sorry, there was a problem retrieving the data: ${error?.detail ?? ""}`
      );
      console.error(error);
      return null;
    }
    return data;
  },
  (
    event_id: number[],
    bbox: string,
    countries: CountriesEnum | CountriesEnum[],
    exposure_key: string
  ) =>
    [sortBy([event_id].flat(), identity), countries, bbox, exposure_key]
      .flat()
      .join()
);
