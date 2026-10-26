"""Lightweight, self-contained HTTP web server for RF Origami Design Studio.

Uses Python standard library (http.server) with zero external pip dependencies.
Serves static assets and REST API endpoints for the web UI.
"""

from __future__ import annotations
import argparse
import json
import mimetypes
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

from rf_origami.web.service import OrigamiWebService


STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.isdir(STATIC_DIR):
    STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "public")


class OrigamiRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for RF Origami Design Studio."""

    def do_OPTIONS(self) -> None:
        """Handle CORS pre-flight requests."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        """Handle GET requests for static files and REST endpoints."""
        url_path = self.path.split("?")[0]

        if url_path == "/api/patterns":
            catalog = OrigamiWebService.get_pattern_catalog()
            self._send_json(catalog)
            return

        if url_path == "/api/design-space":
            ds_info = OrigamiWebService.get_default_design_space()
            self._send_json(ds_info)
            return

        if url_path == "/api/rf/materials":
            materials = OrigamiWebService.get_available_materials()
            self._send_json(materials)
            return

        if url_path == "/api/rf/benchmarks":
            benchmarks = OrigamiWebService.get_validation_benchmarks()
            self._send_json(benchmarks)
            return

        if url_path == "/api/rf/validation":
            self._send_json(OrigamiWebService.get_validation_report())
            return

        if url_path == "/api/absorber/benchmarks":
            benchmarks = OrigamiWebService.get_absorber_benchmarks()
            self._send_json(benchmarks)
            return

        # Serve static assets
        if url_path == "/" or url_path == "":
            url_path = "/index.html"

        file_path = os.path.normpath(os.path.join(STATIC_DIR, url_path.lstrip("/")))

        # Prevent directory traversal attacks
        if not file_path.startswith(STATIC_DIR) or not os.path.isfile(file_path):
            self.send_error(404, f"File not found: {url_path}")
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(500, f"Internal server error: {e}")

    def do_POST(self) -> None:
        """Handle POST requests for geometric generation, folding, absorber MoM, optimization, and fabrication."""
        url_path = self.path.split("?")[0]

        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            req_data = json.loads(post_body)
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON in request body"}, status=400)
            return

        if url_path == "/api/explore":
            try:
                result = OrigamiWebService.run_exploration(req_data)
                self._send_json(result)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/absorber/simulate":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 30.0))
            f_start = float(req_data.get("f_start_ghz", 1.0))
            f_stop = float(req_data.get("f_stop_ghz", 6.0))
            num_points = int(req_data.get("num_points", 31))
            sub_mat = str(req_data.get("substrate_material", "kapton"))
            cond_mat = str(req_data.get("conductor_material", "copper"))
            ground_backed = bool(req_data.get("ground_backed", True))
            thickness = float(req_data.get("substrate_thickness_mm", 0.5))
            polarization = str(req_data.get("polarization", "linear_x"))
            incidence_deg = float(req_data.get("incidence_angle_deg", 0.0))
            azimuth_deg = float(req_data.get("azimuth_angle_deg", 0.0))
            sheet_res = float(req_data.get("sheet_resistance", 0.0))
            material_tags = req_data.get("material_tags", None)

            try:
                sim_res = OrigamiWebService.simulate_absorber(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    f_start_ghz=f_start,
                    f_stop_ghz=f_stop,
                    num_points=num_points,
                    substrate_material=sub_mat,
                    conductor_material=cond_mat,
                    ground_backed=ground_backed,
                    substrate_thickness_mm=thickness,
                    polarization=polarization,
                    incidence_angle_deg=incidence_deg,
                    azimuth_angle_deg=azimuth_deg,
                    sheet_resistance=sheet_res,
                    material_tags=material_tags,
                )
                self._send_json(sim_res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/absorber/fold-sweep":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angles = req_data.get("fold_angles", [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0])
            f_start = float(req_data.get("f_start_ghz", 1.0))
            f_stop = float(req_data.get("f_stop_ghz", 6.0))
            num_points = int(req_data.get("num_points", 25))
            sub_mat = str(req_data.get("substrate_material", "kapton"))
            cond_mat = str(req_data.get("conductor_material", "copper"))
            ground_backed = bool(req_data.get("ground_backed", True))
            thickness = float(req_data.get("substrate_thickness_mm", 0.5))
            polarization = str(req_data.get("polarization", "linear_x"))

            try:
                sweep_res = OrigamiWebService.run_absorber_fold_sweep(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angles=fold_angles,
                    f_start_ghz=f_start,
                    f_stop_ghz=f_stop,
                    num_points=num_points,
                    substrate_material=sub_mat,
                    conductor_material=cond_mat,
                    ground_backed=ground_backed,
                    substrate_thickness_mm=thickness,
                    polarization=polarization,
                )
                self._send_json(sweep_res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/absorber/optimize":
            target_freq = float(req_data.get("target_frequency_ghz", 2.45))
            min_abs = float(req_data.get("min_absorption", 0.90))
            pop_size = int(req_data.get("population_size", 15))
            gens = int(req_data.get("generations", 3))

            try:
                opt_res = OrigamiWebService.run_absorber_optimization(
                    target_frequency_ghz=target_freq,
                    min_absorption=min_abs,
                    population_size=pop_size,
                    generations=gens,
                )
                self._send_json(opt_res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/fabrication/export":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 30.0))
            design_id = str(req_data.get("design_id", "ORIGAMI-ABS-001"))
            sub_mat = str(req_data.get("substrate_material", "Kapton Polyimide"))
            cond_mat = str(req_data.get("conductor_material", "Rolled Annealed Copper (35 um)"))
            thickness = float(req_data.get("substrate_thickness_mm", 0.5))

            try:
                zip_bytes = OrigamiWebService.export_fabrication(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    design_id=design_id,
                    substrate_material=sub_mat,
                    conductor_material=cond_mat,
                    substrate_thickness_mm=thickness,
                )
                import base64
                b64_zip = base64.b64encode(zip_bytes).decode("utf-8")
                self._send_json({
                    "design_id": design_id,
                    "filename": f"{design_id}_fabrication_package.zip",
                    "data_base64": b64_zip,
                    "size_bytes": len(zip_bytes),
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/experiments/compare":
            csv_data = str(req_data.get("csv_data", ""))
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 30.0))
            sub_mat = str(req_data.get("substrate_material", "kapton"))
            cond_mat = str(req_data.get("conductor_material", "copper"))

            try:
                comp_res = OrigamiWebService.compare_measurement(
                    csv_data=csv_data,
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    substrate_material=sub_mat,
                    conductor_material=cond_mat,
                )
                self._send_json(comp_res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/metasurface/phase":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angles = req_data.get("fold_angles", [0.0, 15.0, 30.0, 45.0, 60.0, 75.0])
            f_start = float(req_data.get("f_start_ghz", 2.0))
            f_stop = float(req_data.get("f_stop_ghz", 6.0))
            num_points = int(req_data.get("num_points", 21))
            try:
                res = OrigamiWebService.analyze_metasurface_phase(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angles=fold_angles,
                    f_start_ghz=f_start,
                    f_stop_ghz=f_stop,
                    num_points=num_points,
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/metasurface/polarization":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 30.0))
            f_start = float(req_data.get("f_start_ghz", 2.0))
            f_stop = float(req_data.get("f_stop_ghz", 6.0))
            num_points = int(req_data.get("num_points", 21))
            try:
                res = OrigamiWebService.analyze_metasurface_polarization(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    f_start_ghz=f_start,
                    f_stop_ghz=f_stop,
                    num_points=num_points,
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/metasurface/rcs":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 30.0))
            freq_ghz = float(req_data.get("frequency_ghz", 2.45))
            try:
                res = OrigamiWebService.calculate_metasurface_rcs(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    frequency_ghz=freq_ghz,
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/metasurface/ecm":
            length = float(req_data.get("facet_length_mm", 25.0))
            fold_angle = float(req_data.get("fold_angle", 30.0))
            f_start = float(req_data.get("f_start_ghz", 1.0))
            f_stop = float(req_data.get("f_stop_ghz", 6.0))
            num_points = int(req_data.get("num_points", 31))
            try:
                res = OrigamiWebService.evaluate_metasurface_ecm(
                    facet_length_mm=length,
                    fold_angle_deg=fold_angle,
                    f_start_ghz=f_start,
                    f_stop_ghz=f_stop,
                    num_points=num_points,
                )
                self._send_json(res)
            except Exception as e:
                self._send_json({"error": str(e)}, status=500)
            return



        if url_path == "/api/rf/simulate":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 35.0))
            f_start = float(req_data.get("f_start_ghz", 1.0))
            f_stop = float(req_data.get("f_stop_ghz", 6.0))
            num_points = int(req_data.get("num_points", 21))
            sub_mat = str(req_data.get("substrate_material", "kapton"))
            cond_mat = str(req_data.get("conductor_material", "copper"))
            port_z0 = float(req_data.get("port_z0", 50.0))
            material_tags = req_data.get("material_tags", None)

            try:
                sim_res = OrigamiWebService.simulate_rf(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    f_start_ghz=f_start,
                    f_stop_ghz=f_stop,
                    num_points=num_points,
                    substrate_material=sub_mat,
                    conductor_material=cond_mat,
                    port_z0=port_z0,
                    material_tags=material_tags,
                )
                self._send_json(sim_res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/rf/fold-sweep":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angles = req_data.get("fold_angles", [15.0, 30.0, 45.0, 60.0, 75.0])
            f_start = float(req_data.get("f_start_ghz", 1.0))
            f_stop = float(req_data.get("f_stop_ghz", 6.0))
            num_points = int(req_data.get("num_points", 15))
            sub_mat = str(req_data.get("substrate_material", "kapton"))
            cond_mat = str(req_data.get("conductor_material", "copper"))

            try:
                sweep_res = OrigamiWebService.run_rf_fold_sweep(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angles=fold_angles,
                    f_start_ghz=f_start,
                    f_stop_ghz=f_stop,
                    num_points=num_points,
                    substrate_material=sub_mat,
                    conductor_material=cond_mat,
                )
                self._send_json(sweep_res)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path == "/api/fold/export":
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 30.0))
            as_folded = bool(req_data.get("as_folded", False))
            title = req_data.get("title", None)

            try:
                fold_data = OrigamiWebService.export_fold_file(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    as_folded=as_folded,
                    title=title,
                )
                self._send_json(fold_data)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
            return

        if url_path in ("/api/generate", "/api/fold"):
            pattern_type = req_data.get("pattern_type", "miura_ori")
            params = req_data.get("params", {})
            fold_angle = float(req_data.get("fold_angle", 30.0))
            material_tags = req_data.get("material_tags", {})

            try:
                result = OrigamiWebService.generate_and_fold(
                    pattern_type=pattern_type,
                    params=params,
                    fold_angle_deg=fold_angle,
                    material_tags=material_tags,
                )
                self._send_json(result)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self._send_json({"error": str(e)}, status=500)
        else:
            self.send_error(404, f"API endpoint not found: {url_path}")

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        """Helper to send JSON response."""
        resp_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(resp_bytes)

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress noisy request logs, print concise messages."""
        sys.stderr.write(f"[RF Origami Studio] {args[0]} {args[1]}\n")


def run_server(port: int | None = None, host: str | None = None) -> None:
    """Start local or hosted RF Origami Design Studio server."""
    actual_port = port if port is not None else int(os.environ.get("PORT", 8080))
    actual_host = host if host is not None else os.environ.get("HOST", "127.0.0.1")
    server_address = (actual_host, actual_port)
    httpd = HTTPServer(server_address, OrigamiRequestHandler)
    print("=" * 70, flush=True)
    print(f"  RF ORIGAMI DESIGN STUDIO", flush=True)
    print(f"  Server Running: http://{actual_host}:{actual_port}", flush=True)
    print("  Press Ctrl+C to stop the server.", flush=True)
    print("=" * 70, flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    default_port = int(os.environ.get("PORT", 8080))
    default_host = os.environ.get("HOST", "127.0.0.1")
    parser = argparse.ArgumentParser(description="RF Origami Design Studio Web Server")
    parser.add_argument("--port", type=int, default=default_port, help=f"Port to listen on (default: {default_port})")
    parser.add_argument("--host", type=str, default=default_host, help=f"Host address (default: {default_host})")
    args = parser.parse_args()
    run_server(port=args.port, host=args.host)
