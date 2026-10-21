# Packages the TypeScript Connector SDK + the in-memory SampleConnector as
# a single, runnable image, mirroring python/Dockerfile.
#
#   docker build -t connector-sdk-ts .
#   docker run --rm connector-sdk-ts
#
# should print a "success" SyncResult and exit 0.
#
# Two stages: the first has the full devDependencies (typescript) needed to
# compile; the second ships only the compiled output and zod (the one
# runtime dependency), so the final image doesn't carry typescript/vitest.

FROM node:22-slim AS build

WORKDIR /app

COPY package.json package-lock.json* ./
# devDependencies included on purpose: this stage only compiles, it is
# discarded after `dist/` is copied out below.
RUN npm ci

COPY tsconfig.build.json ./
COPY src ./src
# src/testing/** is excluded by tsconfig.build.json -- it imports vitest
# (a devDependency) and is test-only code, not part of the shipped SDK.
RUN npm run build


FROM node:22-slim

WORKDIR /app

COPY package.json package-lock.json* ./
# --omit=dev: only zod, the SDK's one runtime dependency, is installed.
RUN npm ci --omit=dev

COPY --from=build /app/dist ./dist

RUN useradd --create-home --uid 1000 sdk
USER sdk

ENTRYPOINT ["node", "dist/scripts/runSample.js"]
