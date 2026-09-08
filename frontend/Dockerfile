# 第一阶段：构建前端。
# 先保持与本地已验证的 Node 版本一致。
# alpine 是体积较小的 Linux 基础环境。
FROM node:22.18.0-alpine AS builder

WORKDIR /app

# 先复制依赖清单。
# 仅修改业务代码时，Docker 有机会复用依赖安装缓存。
COPY package.json package-lock.json ./

# 构建需要 TypeScript、Vite 等开发依赖，因此不能省略 dev。
RUN npm ci

# 复制构建入口与配置。
# 这里的源路径相对于 frontend 构建上下文，而不是仓库根目录。
COPY index.html ./
COPY tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY vite.config.ts ./
COPY src ./src

# 这是构建参数，不是运行时读取的服务器配置。
# 构建后的浏览器代码会请求同源的 /api/...。
# 这里只允许公开配置，绝不能传入 JWT 密钥或 DeepSeek Key。
ARG VITE_API_BASE_URL=/api

# 把参数提供给本次构建进程。
# Vite 将它替换进生成的 JavaScript。
RUN VITE_API_BASE_URL="$VITE_API_BASE_URL" npm run build


# 第二阶段：运行静态文件服务器。
# 使用非 root 的 Nginx 镜像，默认使用容器端口 8080。
FROM nginxinc/nginx-unprivileged:stable-alpine AS runtime

# 下一步会创建这个配置文件。
# 只替换站点配置，不替换镜像自带的整个 nginx.conf。
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 只从 builder 阶段复制构建产物。
# 不复制 Node、node_modules 或前端源代码目录。
COPY --from=builder /app/dist /usr/share/nginx/html

# 声明容器服务端口。
# EXPOSE 不会自动把端口发布到宿主机，之后由 Compose 配置。
EXPOSE 8080

# 前台运行，让 Nginx 成为容器主进程。
CMD ["nginx", "-g", "daemon off;"]