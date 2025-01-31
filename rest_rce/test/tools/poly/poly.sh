#! /bin/sh

USAGE="Usage: poly.sh x [n]"

if [ $# -eq 0 ] || [ $# -gt 2 ]; then
	echo $USAGE
	exit 1
fi

x=$1

echo "Calculating exp"
echo "Received parameter x="$x

if [ $# -eq 2 ]; then
	n=$2
	echo "Received parameter n="$n
else
	n=2
	echo "Using default exponent "$n
fi

result=1
i=1
while [ $i -le $n ]
do
	result=`expr $result \* $x`
	i=`expr $i + 1`
done
echo "Result:" $result
echo $result > result
