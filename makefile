

#main:
#	g++ -o poly poly.cpp -lppl -lgmp -std=c++0x
	



CFLAGS = -lppl -lgmp -std=c++0x
CC = g++
SRC = poly.cpp 
OBJ = $(SRC:.cpp = .o)

main: $(OBJ)
	$(CC) -o poly $(OBJ) $(CFLAGS)

clean:
	rm -f core *.o