# Table of Contents

## Introduction

- [Repository Overview](./repo_overview.md) - High-level guide to the project structure and components.
- [Technical Overview](./technical_overview.md) - Deep dive into the RAI framework, platform stack, and runtime flow.
- [Demo Description](./demo.md) - Overview of the warehouse demo, video, and objectives.

## Getting Started

- [Quickstart Guide](./quickstart.md) - Fast track to running the demo using Docker Compose.
- [Dependencies](./dependencies.md) - List of system requirements and dependencies.
- [Setup Overview](./setup.md) - General setup information and choosing your configuration.

## Setup Guides

- [Single Machine Setup](./setup_single_machine.md) - Instructions for running everything on one computer.
- [Three-Machine Setup (HIL + Sim + HMI)](./setup_hil_sim_hmi.md) - Guide for a distributed setup resembling a real-world deployment.
- [Simulation Setup](./setup_sim.md) - Detailed instructions for building and configuring O3DE.
- [HMI Setup](./setup_hmi.md) - Instructions for building and running the Human-Machine Interface.
- [HIL Setup](./setup_hil.md) - Instructions for Hardware-in-the-Loop environment setup.

## Running the Demo

- [Running Guide](./running.md) - General instructions for launching the system components.
- [Running HIL + Sim + HMI](./running_hil_sim_hmi.md) - Specific runtime commands for the distributed setup.

## Architecture & Agents

- [Inspection Agent](./inspection_agent.md) - Documentation for the VLM-based anomaly detection agent.
- [Safety Agent with RAG](./safety_agent_with_rag.md) - Guide to the OSHA compliance agent using RAG and Vector DBs.
- [Simulation Overview](./sim_overview.md) - Details on the O3DE environment, robot model, and assets.

## Tutorials & Extension

- [Tutorials](./tutorials.md) - Guides for adding new tools, executors, and customizing the system.
