# Basic API Documentation

Welcome to the documentation for the **Basic API** project.

## Overview

This project is a simple FastAPI application designed for lead generation workflows with OAuth2 + JWT authentication. It provides a modular structure with routers, dependencies, and schemas, making it easy to extend and maintain.

## Key Features

- **REST API Endpoints**: Supports lead pipeline workflows including refresh, retrieve, enrich, and campaign actions.
- **Authentication**: Secure OAuth2 + JWT authentication with support for a single admin user.
- **Flexible Login**: Users can authenticate using their username, email, or phone number.
- **Modular Architecture**: Organized into routers, dependencies, and schemas for better code management.
- **Environment Configuration**: Uses `.env` files for managing configuration and secrets.

## Navigation

- [Setup Guide](setup.md): Instructions on how to install, configure, and run the application.
- [API Reference](api.md): Detailed documentation of the available API endpoints.
- [Authentication](authentication.md): Explanation of the authentication flow and token management.
- [Schemas](schemas.md): Description of the data models used in the API.
