FROM node:22-alpine

WORKDIR /app/tools/shujuji_annotation
COPY . .

WORKDIR /app/tools/shujuji_annotation/annotation_platform
ENV NODE_ENV=production
ENV PORT=8787
ENV SHUJUJI_DATA_ROOT=/data/shujuji_annotation

EXPOSE 8787
CMD ["node", "server.js"]
