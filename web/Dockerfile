FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && corepack prepare pnpm@9.15.4 --activate && pnpm install --frozen-lockfile
COPY . .
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN pnpm build

FROM node:20-alpine
WORKDIR /app
RUN addgroup -g 10001 app && adduser -D -u 10001 -G app app
COPY --from=builder --chown=app:app /app ./
USER app
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start"]
