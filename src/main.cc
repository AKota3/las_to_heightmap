#include <memory>
#include <iostream>
#include <stdint.h>

#include <pdal/PointTable.hpp>
#include <pdal/PointView.hpp>
#include <pdal/io/LasReader.hpp>
#include <pdal/io/LasHeader.hpp>
#include <pdal/Options.hpp>

#include <png++/png.hpp>

using namespace std;

#define DEFAULT_WIDTH  2048
#define DEFAULT_HEIGHT 2048

std::map<std::string, std::string> parseArgs(int argc, char* argv[]) {
	std::map<std::string, std::string> args;

	for (int i = 1; i < argc; ++i) {
		std::string arg = argv[i];
		if (arg[0] == '-') {
			std::string key = arg.substr(1);
			if ((i + 1) < argc && argv[i + 1][0] != '-') {
				std::cout << key << ": " << argv[i + 1][0] << std::endl;
				args[key] = argv[++i];
			} else {
				args[key] = "true";
			}
		}
	}

	return args;
}

struct Point {
	double x, y, z;
	int classification;
	uint8_t intensity;

	double distance2(const Point &p) const {
		double dx = p.x - x;
		double dy = p.y - y;
		double dz = p.z - z;
		return dx*dx + dy*dy + dz*dz;
	}

	double distance(const Point &p) const {
		return sqrt(distance2(p));
	}
};

class LasToHeightmap {
	pdal::LasReader las_reader;

	double offsetX;
	double offsetY;
	double offsetZ;
	double scaleX;
	double scaleY;

	int output_width;
	int output_height;

	void addPoint(double x, double y, double z, int classification, int intensity) {
		x = (x - offsetX) * scaleX;
		y = (y - offsetY) * scaleY;
		z = (z - offsetZ);
		intensity /= 256;

		/* Skip vegetation, "other", and noise */
		if (classification == 3 || classification == 4 || classification == 7 || classification == 8)
			return;

		if ((int)x >= output_width)
			x = output_width - 1;
		if ((int)y >= output_height)
			y = output_height - 1;
		if (x < 0)
			x = 0;
		if (y < 0)
			y = 0;

		if (intensity > 255)
			intensity = 255;

		Point point = {x,y,z,classification,(uint8_t)intensity};

		pointsAt(x, y)->push_back(point);
	}

	public:

	std::vector<Point> *pointMatrix;

	LasToHeightmap(int width, int height, pdal::Options &las_opts) {
		output_width = width;
		output_height = height;
		las_reader.setOptions(las_opts);

		pointMatrix = new std::vector<Point>[width * height]();
	}

	void perform() {
		pdal::PointTable table;
		las_reader.prepare(table);
		pdal::PointViewSet point_view_set = las_reader.execute(table);
		pdal::PointViewPtr point_view = *point_view_set.begin();
		pdal::Dimension::IdList dims = point_view->dims();
		pdal::LasHeader las_header = las_reader.header();

		std::cerr << "X: " << las_header.minX() << " to " << las_header.maxX() << std::endl;
		std::cerr << "Y: " << las_header.minY() << " to " << las_header.maxY() << std::endl;
		std::cerr << "Z: " << las_header.minZ() << " to " << las_header.maxZ() << std::endl;
		std::cerr << "output: " << output_width << "x" << output_height << std::endl;

		offsetX = las_header.minX();
		offsetY = las_header.maxY();

		offsetZ = -16;

		scaleX = output_width/1000.0;
		scaleY = -output_height/1000.0;

		for (pdal::PointId idx = 0; idx < point_view->size(); ++idx) {
			using namespace pdal::Dimension;
			double x = point_view->getFieldAs<double>(Id::X, idx);
			double y = point_view->getFieldAs<double>(Id::Y, idx);
			double z = point_view->getFieldAs<double>(Id::Z, idx);

			int classification = point_view->getFieldAs<int>(Id::Classification, idx);
			int intensity = point_view->getFieldAs<int>(Id::Intensity, idx);

			addPoint(x, y, z, classification, intensity);
		}
	}

	std::vector<Point> *pointsAt(int x, int y) {
		if (x < 0 || x >= output_width || y < 0 || y >= output_height) {
			return NULL;
		} else {
			return &pointMatrix[y * output_width + x];
		}
	}

	/* Makes a "fake" point with some heuristics on the points around it */
	Point pointAt(int x, int y, int range=3) {
		Point point = {(double)x + 0.5, (double)y + 0.5, 0, 0, 0};
		std::vector<Point> neighbourPoints;
		neighbourPoints.reserve(2048);

		auto addPoints = [&](std::vector<Point> *v) {
			if (v) {
				std::copy(v->begin(), v->end(), std::back_inserter(neighbourPoints));
			}
		};

		for (int dy = -range; dy <= range; dy++) {
			for (int dx = -range; dx <= range; dx++) {
				addPoints(pointsAt(x+dx, y+dy));
			}
		}

		if(neighbourPoints.empty()) {
			return point;
		} else {
			std::nth_element(
					neighbourPoints.begin(),
					neighbourPoints.begin() + (neighbourPoints.size() / 2),
					neighbourPoints.end(),
					[](const Point &p1, const Point &p2) { return p1.z < p2.z; }
					);

			Point medianPoint = neighbourPoints[neighbourPoints.size() / 2];
			point.z = medianPoint.z;

			auto representativePoint = std::min_element(
					neighbourPoints.begin(), neighbourPoints.end(),
					[&](const Point &p1, const Point &p2) { return point.distance2(p1) < point.distance2(p2); }
					);
			if (representativePoint != neighbourPoints.end()) {
				/* If we can find a point near out median z point, use its intensity */
				//point.intensity = representativePoint->intensity;
				point.intensity = representativePoint->intensity;
			} else {
				/* Otherwise, take the average */
				cerr << "this should never happen" << endl;
				point.intensity = 255; /*DEBUG*/
			}

			//point.intensity = medianPoint.intensity;

			return point;
		}
	}

};

void processPointsToGrayImage(png::image<png::gray_pixel_16> &output_image, LasToHeightmap &lasToHeightmap, unsigned int width, unsigned int height) {
	for (unsigned int y = 0; y < height; y++) {
		for (unsigned int x = 0; x < width; x++) {
			Point p = lasToHeightmap.pointAt(x, y);
			double z = p.z;
			if (z < 0)
				z = 0;
			unsigned short iz = z * 256;
			output_image[y][x] = png::gray_pixel_16(iz);
		}
	}
}

void processPointsToRGBImage(png::image<png::rgb_pixel> &output_image, LasToHeightmap &lasToHeightmap, unsigned int width, unsigned int height) {
	for (unsigned int y = 0; y < height; y++) {
		for (unsigned int x = 0; x < width; x++) {
			Point p = lasToHeightmap.pointAt(x, y);
			double z = p.z;
			if (z < 0)
				z = 0;
			unsigned short iz = z * 256;
			// output_image[y][x] = png::rgb_pixel(p.intensity, iz >> 8, iz & 0xff);
			output_image[y][x] = png::rgb_pixel(z, z, z);
		}
	}
}

int main(int argc, char *argv[]) {
	auto args = parseArgs(argc, argv);
	for (const auto& [key, value] : args) {
		std::cout << "-" << key << ": " << value << std::endl;
	}

	if (args.count("help") || args.count("h")) {
		std::cout << "Usage: " << argv[0] << " -i <input file: required> -o <output file: required> -W <width: default 2048> -H <height: default: 2048>" << std::endl;
		return 0;
	}
	
	if (!args.count("i")) {
		std::cout << "-i <input file> option is required" << std::endl;
		return 1;
	}
	std::string input_filename = args["i"];
	
	if (!args.count("o")) {
		std::cout << "-o <output file> option is required" << std::endl;
		return 1;
	}
	std::string output_filename = args["o"];

	unsigned int width = DEFAULT_WIDTH;
	unsigned int height = DEFAULT_HEIGHT;
	try {
		if (args.count("W")) {
			width = std::stoul(args["W"]);
		}
		if (args.count("H")) {
			height = std::stoul(args["H"]);
		}
	} catch (const std::invalid_argument &e) {
		std::cerr << "Error: Width and height must be valid integers." << std::endl;
		return 1;
	}
	
	bool is_gray = true;
	if (args.count("rgb")) {
		is_gray = false;
	}

	try {
		cout << "Collecting all points..." << endl;
		pdal::Option las_opt("filename", input_filename);
		pdal::Options las_opts;
		las_opts.add(las_opt);
		LasToHeightmap lasToHeightmap(width, height, las_opts);
		lasToHeightmap.perform();

		cout << "Creating heightmap..." << endl;
		if (is_gray) {
			png::image<png::gray_pixel_16> output_image(width, height);
			processPointsToGrayImage(output_image, lasToHeightmap, width, height);
			output_image.write(output_filename);
		} else {
			png::image<png::rgb_pixel> output_image(width, height);
			processPointsToRGBImage(output_image, lasToHeightmap, width, height);
			output_image.write(output_filename);
		}

		// output_image.write(output_filename);
	} catch (const std::exception &e) {
		std::cerr << "ERROR: " << e.what() << std::endl;
		return 1;
	}

	return 0;
}
